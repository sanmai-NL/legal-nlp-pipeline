from contextlib import ContextDecorator
from logging import info
from logging import warning
from os import chmod
from os.path import isdir
from os.path import normpath
from shutil import move
from tempfile import mkdtemp


class TempDir(ContextDecorator):
    def __init__(self, base_dir_path: str, suffix: str, directory_permissions:
                 oct, method: str):
        """
        Constructor that renews a base directory path.

        :param base_dir_path: the base directory path.
        :param suffix: suffix to temporary base directory.
        :param directory_permissions: octal filesystem permissions.
        :param method: one of 'new_but_restore_mtimes', 'new'.
        :return: None
        """
        self.base_dir_path = normpath(base_dir_path)
        self.directory_permissions = directory_permissions
        self.suffix = suffix
        self.method = method
        self.temp_base_dir_path = mkdtemp(suffix=suffix)

    def __enter__(self):

        info("Working in temporary base directory '{temp_base_dir_path}', to "
             "be moved to '{base_dir_path}'. ".format(
                 temp_base_dir_path=self.temp_base_dir_path,
                 base_dir_path=self.base_dir_path))
        return self

    def __exit__(self, *exc):
        if isdir(self.base_dir_path):
            bak_base_dir_path = mkdtemp(suffix=self.suffix)
            warning(
                "Trying to back up existent base directory '{base_dir_path}' "
                "to '{bak_base_dir_path}' ... ".format(
                    base_dir_path=self.base_dir_path,
                    bak_base_dir_path=bak_base_dir_path))
            move(src=self.base_dir_path, dst=bak_base_dir_path)

        chmod(self.temp_base_dir_path, self.directory_permissions)
        # TODO: use keyword arguments once Python >3.4
        move(src=self.temp_base_dir_path, dst=self.base_dir_path)

        if exc is not None:
            raise exc
