'use strict';

/*
 * VERBATIM REFERENCE — DO NOT USE, DO NOT WIRE INTO ANYTHING.
 *
 * This is Sam's originally pasted `looksLikeImplementation` /
 * `buildCapabilityIdentifierPattern`, unmodified, kept only so the test
 * runner can show real before/after verdicts against the fixed version in
 * looksLikeImplementation.js.
 *
 * `containsCapabilityToken` was never supplied and does not exist anywhere
 * in this repository (confirmed by search — the repo held nothing but a
 * README before this change). The stand-in below is the simplest possible
 * reading consistent with how the original code calls it: true if the
 * line contains ANY of the capability's token patterns. That reading is
 * NOT itself one of the four defects — it is deliberately kept identical
 * in both the buggy and fixed versions (see the design note in
 * looksLikeImplementation.js) so the comparison isolates the four defects
 * that ARE in the pasted code, rather than a guess about a function that
 * was missing entirely.
 */
function containsCapabilityToken(line, patterns) {
    if (!patterns || patterns.length === 0) {
        return false;
    }
    return patterns.some((pattern) => pattern.test(line));
}

function looksLikeImplementation(line, patterns) {
    if (!containsCapabilityToken(line, patterns)) {
        return false;
    }

    if (
        /\b(?:async\s+)?function\s+[A-Za-z_$][\w$]*\s*\(/i.test(line)
    ) {
        return true;
    }

    if (
        /\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>/i.test(line)
    ) {
        return true;
    }

    if (
        /\bclass\s+[A-Za-z_$][\w$]*/i.test(line)
    ) {
        return true;
    }

    if (
        /\bdef\s+[A-Za-z_][\w]*\s*\(/i.test(line)
    ) {
        return true;
    }

    if (
        /\basync\s+def\s+[A-Za-z_][\w]*\s*\(/i.test(line)
    ) {
        return true;
    }

    if (
        /\bfunc\s+(?:\([^)]*\)\s*)?[A-Za-z_][\w]*\s*\(/i.test(line)
    ) {
        return true;
    }

    if (
        /\btype\s+[A-Za-z_][\w]*\s+struct\s*\{/i.test(line)
    ) {
        return true;
    }

    if (
        /\b(?:pub\s+)?(?:async\s+)?fn\s+[A-Za-z_][\w]*\s*\(/i.test(line)
    ) {
        return true;
    }

    if (
        /\b(?:pub\s+)?struct\s+[A-Za-z_][\w]*/i.test(line) ||
        /\bimpl(?:<[^>]+>)?\s+[A-Za-z_][\w]*/i.test(line)
    ) {
        return true;
    }

    const capabilityIdentifierPattern =
        buildCapabilityIdentifierPattern(patterns);

    if (
        capabilityIdentifierPattern &&
        capabilityIdentifierPattern.test(line)
    ) {
        if (
            /\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=/i.test(line) ||
            /\b[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?(?:function|\([^)]*\)\s*=>)/i.test(line)
        ) {
            return true;
        }

        if (
            /\b[A-Za-z_][\w]*\s*=/i.test(line) ||
            /\b(?:var|type)\s+[A-Za-z_][\w]*/i.test(line)
        ) {
            return true;
        }

        if (
            /\b(?:handler|service|controller|manager|provider|adapter|implementation)\b/i.test(line) &&
            /[=:({]/.test(line)
        ) {
            return true;
        }
    }

    return false;
}

function buildCapabilityIdentifierPattern(patterns) {
    if (!patterns || patterns.length === 0) {
        return null;
    }

    const sources = patterns
        .map(pattern => pattern.source)
        .filter(Boolean);

    if (sources.length === 0) {
        return null;
    }

    return new RegExp(
        `(?:${sources.join('|')})`,
        'i'
    );
}

module.exports = {
    containsCapabilityToken,
    looksLikeImplementation,
    buildCapabilityIdentifierPattern,
};
