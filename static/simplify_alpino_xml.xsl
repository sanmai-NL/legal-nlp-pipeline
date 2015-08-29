<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    exclude-result-prefixes="xs math"
    version="1.0">
    <xsl:output indent="yes" method="xml"/>

    <xsl:template
        match="/">
        <xsl:apply-templates select='alpino_ds'/>
        <xsl:apply-templates select='text()'/>
    </xsl:template>

    <xsl:template
        match='node'>
        <xsl:copy>
            <xsl:copy-of
                select="@begin"/>
            <xsl:copy-of
                select="@end"/>
            <xsl:copy-of
                select="@pos"/>
            <xsl:copy-of
                select="@postag"/>
            <xsl:copy-of
                select="@rel"/>
            <xsl:copy-of
                select="@word"/>
            <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="text()"/>

</xsl:stylesheet>
