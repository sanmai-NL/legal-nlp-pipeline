#!/bin/sh

base_port_number=42424 ;
save_traps=$(trap)

ALPINO_HOME='/opt/Alpino/Alpino/' export ALPINO_HOME
PATH="${PATH}:${ALPINO_HOME}/bin/" export PATH

produce_html_documentation() {
    pandoc --toc -f markdown_github --highlight-style=pygments -s "${VIRTUAL_ENV:-dev/null}/share/README.md"
}

inventorize_parsings() {
    printf '%d rulings, spanning %d sentences.\n' \
        $(find "$1" -mindepth 0 -maxdepth 1 -type d -name 'ECLI*' 2> /dev/null | wc -l) $(find "$1" -mindepth 1 -type f -name '*.xml' 2> /dev/null | wc -l)
}

# TODO: Use \0 as separator
iterate_over_parsings() {
    # First argument: parsings dir path.
    # Second argument: XPath string.
    find "$1" -mindepth 1 -type f -name '*.xml' -exec xml sel -t -m '/alpino_ds' --if "$2" -f -n '{}' +
}

simplify_parsing() {
    xml tr "${VIRTUAL_ENV:-dev/null}/share/simplify_alpino_xml.xsl" "$1" > "$2"
}

limit_to_unique_parsings() {
   iterate_over_parsings | xargs -n 1 dirname | uniq
}

show_tree_svg_of_parsing() {
    ecli=$(realpath --relative-to $(dirname $(dirname "$1")) $(dirname "$1")) &&
    sentence_index=$(basename "$1") &&
    svg_file_suffix="${ecli}__${sentence_index}.svg" &&
    tree_file_path=$(mktemp --suffix="${svg_file_suffix}") &&
    _svg_file_of_parsing "${tree_file_path}" < "$1" &&
    printf '%s\n' "Shown '${tree_file_path}'."
}

_svg_file_of_parsing() {
    # 1 output: Alpino parsing tree SVG file
    xml tr "${VIRTUAL_ENV:-dev/null}/share/xml2tree-sonar.xsl" > "$1" - &&
    xdg-open "$1"
    # TODO: clobber prevention
}

clean_up() {
    eval "${save_traps}" ;
    if [ "$1" -ne 0 ]; then
        # printf 'Something went wrong.\n%s\n' "$(uptime)" | mailx -r "$USER@$(hostname) <S.N.Maijers@gmail.com>" -s 'legal_nlp_pipeline failed '"($1)" "$USER@$(hostname) <S.N.Maijers@gmail.com>" # TODO:
        printf '%s\n' "An error (exit status: $1) occurred. " 1>&2 ;
    fi

    return $1 ;
}

start_legal_nlp_pipeline_under_systemd() {
    python -W all -OO -m 'legal_nlp_pipeline' "$@" || return $(clean_up $?) ;
}

start_legal_nlp_pipeline() {
    # TODO: sudo -E nice -n -15 sudo -E -u '#'$(id -u) -g '#'$(id -g) python -OO -m 'legal_nlp_pipeline' "$@" || clean_up

    trap clean_up SIGINT ;

    printf '\n%s\n' 'Starting legal_nlp_pipeline (if needed) ... ' ;

    #printenv PATH VIRTUAL_ENV PYTHONHOME PYTHONPATH
    #return

    tmux has-session -t 'legal_nlp_pipeline' 2> /dev/null ||
    tmux new-session -d -s 'legal_nlp_pipeline' ||
    return $(clean_up $?) ;
    #tmux set-option -ga update-environment ' PATH VIRTUAL_ENV'
    # tmux set-option -gar update-environment ' PATH VIRTUAL_ENV'
    #tmux set-environment -t 'legal_nlp_pipeline' PATH "$PATH"
    tmux set-environment -t 'legal_nlp_pipeline' PATH2 "$PATH"
    tmux set-environment -t 'legal_nlp_pipeline' VIRTUAL_ENV "$VIRTUAL_ENV"
    tmux set-option -t 'legal_nlp_pipeline' default-shell '/bin/sh'
    #tmux set-environment -t 'legal_nlp_pipeline' PYTHONHOME "$PYTHONHOME"
    #tmux set-environment -t 'legal_nlp_pipeline' PYTHONPATH "$PYTHONPATH"

    #  2> /tmp/prob.txt
    command1="printenv PATH VIRTUAL_ENV PYTHONHOME PYTHONPATH > /tmp/prob1.txt; bash"
    command=". $VIRTUAL_ENV/bin/activate && python -W all -OO -m legal_nlp_pipeline $@"
    tmux new-window -n 'legal_nlp_pipeline' -t 'legal_nlp_pipeline' "${command}" ||
    return $(stop_legal_nlp_pipeline || clean_up $?) ;
    #tmux set-environment -t 'legal_nlp_pipeline' PATH "$PATH"

    tmux attach -t 'legal_nlp_pipeline' ||
    return $(clean_up $?) ;
}

stop_legal_nlp_pipeline() {
   printf '%s\n' 'Stopping legal_nlp_pipeline ... ' 1>&2;
   tmux send-keys -t "legal_nlp_pipeline:legal_nlp_pipeline" '^C' ; # TODO: error handling
   sleep 2 ;
   tmux kill-window -t 'legal_nlp_pipeline:legal_nlp_pipeline' || return $(clean_up $?)
   # tmux kill-session -t legal_nlp_pipeline ;
}

start_alpino_instances() {
    alpino_base_invocation='Alpino -veryfast -notk assume_input_is_tokenized=on current_ref=1 pos_tagger=on xml_format_frame=on end_hook=xml server_kind=parse user_max=190000 -init_dict_p batch_command=alpino_server' ;
    CPU_core_index=-1 ;
    port_number=$((base_port_number - 1)) ;
    prioritized_sandbox_invocation="sudo -E nice -n -15 sudo -E -u \#$(id -u) -g \#$(id -g)" ;

    tmux has-session -t 'legal_nlp_pipeline' || tmux new-session -d -s 'legal_nlp_pipeline' ;
    trap clean_up SIGINT ;

    while [ "$CPU_core_index" -lt "$(($(nproc) - 1))" ]; do
         CPU_core_index=$(($CPU_core_index + 1)) ;
         taskset_invocation="taskset -a -c ${CPU_core_index}" ;
         port_number=$((port_number + 1)) ;
         alpino_invocation="${alpino_base_invocation} server_port=${port_number}" ;

         printf '\n%s\n' "Starting Alpino server listening on port ${port_number} with affinity to CPU core ${CPU_core_index} ... " ;
         tmux new-window -t 'legal_nlp_pipeline' -n "Alpino_core_${CPU_core_index}_port_${port_number}" "${taskset_invocation} ${prioritized_sandbox_invocation} ${alpino_invocation}" || return $(clean_up $?) ;
         tmux attach -t 'legal_nlp_pipeline' || return $(clean_up $?) ;
    done ;

    clean_up 0;
}

stop_alpino_classifier_instances() {
   printf '%s\n' 'Stopping legal_nlp_pipeline ... ' 1>&2;
   CPU_core_index=-1 ;
   port_number=$((base_port_number - 1)) ;
   while [ "$CPU_core_index" -lt "$(($(nproc) - 1))" ]; do
       CPU_core_index=$(($CPU_core_index + 1)) ;
       port_number=$((port_number + 1)) ;
       tmux send-keys -t "legal_nlp_pipeline:Alpino_core_${CPU_core_index}_port_${port_number}" '^C' ;
       sleep 2 ;
       tmux kill-window -t "legal_nlp_pipeline:Alpino_core_${CPU_core_index}_port_${port_number}" ;
   done ;
   # tmux kill-session -t legal_nlp_pipeline ;
}


