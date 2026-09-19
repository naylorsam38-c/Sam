'use strict';

/*
 * looksLikeImplementation — static capability-evidence matcher.
 *
 * STANDALONE MODULE. Not wired into any pipeline. Built to fix four proven
 * defects in the version Sam pasted (see FIXES.md in this directory for the
 * full defect-by-defect writeup with real-repo evidence).
 *
 * -----------------------------------------------------------------------
 * DESIGN NOTE — the `patterns` contract had to be DEFINED, not discovered.
 * -----------------------------------------------------------------------
 * The handoff asked us to find out how `patterns` is used elsewhere before
 * fixing this. We searched the whole repository (naylorsam38-c/Sam) and it
 * contains nothing but a README — this function was pasted directly into
 * chat and has never been wired into anything, so there was no real call
 * site to observe. `containsCapabilityToken` also does not exist anywhere
 * in the repo; it is written here from scratch.
 *
 * Because there was nothing to discover, this is a design decision, laid
 * out explicitly for Sam to confirm or override before this is wired into
 * anything:
 *
 *   `patterns` is an array of RegExp, one per significant word ("token")
 *   of the capability's name, in the order those words appear in the
 *   name. For "PDF Export" that is [/pdf/i, /export/i], built by
 *   `patternsForCapabilityName("PDF Export")` below.
 *
 * Two different combinations of that array are needed for two different
 * jobs, and conflating them was the root cause of defect 4:
 *
 *   - `containsCapabilityToken` ORs the tokens together. It is a cheap,
 *     deliberately loose pre-filter: "does this line mention the
 *     capability at all?" A false positive here costs nothing because
 *     nothing is concluded from it alone.
 *   - `buildCapabilityIdentifierPattern` joins the tokens together, IN
 *     ORDER, as one compound-identifier pattern ("pdfExport",
 *     "pdf_export", "PdfExportService", "handlePdfExportNow", ...). This
 *     is the strict check, and it is only ever tested against a NAME this
 *     module has captured from a real declaration — never against the
 *     whole line.
 * -----------------------------------------------------------------------
 */

/** Languages this module actively recognises declarations for. */
const SUPPORTED_LANGUAGES = Object.freeze([
    'javascript', 'typescript', 'python', 'go', 'rust',
    'java', 'csharp', 'kotlin', 'php', 'ruby',
]);

/**
 * Languages explicitly NOT covered. Lines from these will simply never
 * match a construct below and `looksLikeImplementation` returns false for
 * them — that is a coverage gap, not a "no evidence found" verdict, so
 * callers scanning these languages should not treat a `false` as proof of
 * absence.
 */
const UNSUPPORTED_LANGUAGES = Object.freeze([
    'c', 'cpp', 'swift', 'scala', 'objective-c', 'shell', 'sql', 'perl',
]);

/* ------------------------------------------------------------------ */
/* Token / pattern helpers                                             */
/* ------------------------------------------------------------------ */

/** Split a capability name into lowercase word tokens: "PDF Export" -> ["pdf","export"]. */
function tokensForCapabilityName(name) {
    return String(name)
        .split(/[^A-Za-z0-9]+/)
        .filter(Boolean)
        .map((tok) => tok.toLowerCase());
}

/** Build the `patterns` array this module expects, from a plain capability name. */
function patternsForCapabilityName(name) {
    return tokensForCapabilityName(name).map((tok) => new RegExp(escapeRegExp(tok), 'i'));
}

function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Cheap, deliberately loose pre-filter: does the (comment/string-stripped)
 * line mention ANY capability token at all? OR semantics on purpose — see
 * the design note above. Never used on its own to decide anything.
 */
function containsCapabilityToken(line, patterns) {
    if (!patterns || patterns.length === 0) {
        return false;
    }
    return patterns.some((pattern) => pattern.test(line));
}

/**
 * Build the strict, ordered, compound-identifier pattern: tokens must
 * appear in the given order, each optionally separated by `_` or `-`
 * (camelCase boundaries need no separator). Matched only against a
 * captured declaration name, never against a whole line.
 *
 * "PDF Export" -> matches: pdfExport, pdf_export, pdf-export,
 *                          PdfExportService, handlePdfExportNow
 *                 rejects: export (alone), exportPdf (wrong order),
 *                          pdfImport
 */
function buildCapabilityIdentifierPattern(patterns) {
    if (!patterns || patterns.length === 0) {
        return null;
    }
    const tokenSources = patterns.map((pattern) => pattern.source).filter(Boolean);
    if (tokenSources.length === 0) {
        return null;
    }
    const joined = tokenSources.join('[_-]?');
    return new RegExp(joined, 'i');
}

/* ------------------------------------------------------------------ */
/* Comment / string stripping — hand-rolled scanner, not regex.        */
/* Regex cannot correctly track nested quote/comment state across a    */
/* file; a single-pass state machine can. Newlines are preserved so    */
/* line numbers and line-splitting stay correct after stripping.       */
/* ------------------------------------------------------------------ */

const STATE = Object.freeze({
    NORMAL: 'NORMAL',
    LINE_COMMENT: 'LINE_COMMENT',
    BLOCK_COMMENT: 'BLOCK_COMMENT',
    SINGLE_QUOTE: 'SINGLE_QUOTE',
    DOUBLE_QUOTE: 'DOUBLE_QUOTE',
    BACKTICK: 'BACKTICK',
    HASH_COMMENT: 'HASH_COMMENT',
    TRIPLE_SINGLE: 'TRIPLE_SINGLE',
    TRIPLE_DOUBLE: 'TRIPLE_DOUBLE',
    RUBY_BLOCK_COMMENT: 'RUBY_BLOCK_COMMENT',
});

/**
 * Strip `//` and `/* *\/` comments (JS/TS/Go/Rust/Java/C#/Kotlin/PHP),
 * `#` comments (Python/Ruby/PHP), `=begin`/`=end` blocks (Ruby), and
 * `'...'` / `"..."` / `` `...` `` / triple-quoted string contents
 * (Python), replacing stripped characters with spaces so column
 * positions and line boundaries are preserved.
 */
function stripCommentsAndStrings(source) {
    let state = STATE.NORMAL;
    let out = '';
    const n = source.length;
    let i = 0;

    const atLineStart = () => {
        let j = out.length - 1;
        while (j >= 0 && (out[j] === ' ' || out[j] === '\t')) j -= 1;
        return j < 0 || out[j] === '\n';
    };

    while (i < n) {
        const c = source[i];
        const c2 = source[i + 1];
        const c3 = source[i + 2];

        if (state === STATE.NORMAL) {
            if (c === '/' && c2 === '/') {
                state = STATE.LINE_COMMENT;
                out += '  ';
                i += 2;
                continue;
            }
            if (c === '/' && c2 === '*') {
                state = STATE.BLOCK_COMMENT;
                out += '  ';
                i += 2;
                continue;
            }
            if (c === '#') {
                state = STATE.HASH_COMMENT;
                out += ' ';
                i += 1;
                continue;
            }
            if (c === '=' && c2 === 'b' && source.startsWith('=begin', i) && atLineStart()) {
                state = STATE.RUBY_BLOCK_COMMENT;
                out += ' '.repeat(6);
                i += 6;
                continue;
            }
            if (c === "'" && c2 === "'" && c3 === "'") {
                state = STATE.TRIPLE_SINGLE;
                out += '   ';
                i += 3;
                continue;
            }
            if (c === '"' && c2 === '"' && c3 === '"') {
                state = STATE.TRIPLE_DOUBLE;
                out += '   ';
                i += 3;
                continue;
            }
            if (c === "'") {
                state = STATE.SINGLE_QUOTE;
                out += ' ';
                i += 1;
                continue;
            }
            if (c === '"') {
                state = STATE.DOUBLE_QUOTE;
                out += ' ';
                i += 1;
                continue;
            }
            if (c === '`') {
                state = STATE.BACKTICK;
                out += ' ';
                i += 1;
                continue;
            }
            out += c;
            i += 1;
            continue;
        }

        if (state === STATE.LINE_COMMENT) {
            if (c === '\n') {
                state = STATE.NORMAL;
                out += '\n';
            } else {
                out += ' ';
            }
            i += 1;
            continue;
        }

        if (state === STATE.HASH_COMMENT) {
            if (c === '\n') {
                state = STATE.NORMAL;
                out += '\n';
            } else {
                out += ' ';
            }
            i += 1;
            continue;
        }

        if (state === STATE.BLOCK_COMMENT) {
            if (c === '*' && c2 === '/') {
                state = STATE.NORMAL;
                out += '  ';
                i += 2;
                continue;
            }
            out += c === '\n' ? '\n' : ' ';
            i += 1;
            continue;
        }

        if (state === STATE.RUBY_BLOCK_COMMENT) {
            if (source.startsWith('=end', i) && atLineStart()) {
                state = STATE.NORMAL;
                out += '    ';
                i += 4;
                continue;
            }
            out += c === '\n' ? '\n' : ' ';
            i += 1;
            continue;
        }

        if (state === STATE.SINGLE_QUOTE || state === STATE.DOUBLE_QUOTE || state === STATE.BACKTICK) {
            const quote = state === STATE.SINGLE_QUOTE ? "'" : state === STATE.DOUBLE_QUOTE ? '"' : '`';
            if (c === '\\') {
                out += '  ';
                i += 2;
                continue;
            }
            if (c === '\n') {
                /* Unterminated string at end of line: bail back to NORMAL,
                 * a real declaration is never hiding inside a broken string. */
                state = STATE.NORMAL;
                out += '\n';
                i += 1;
                continue;
            }
            if (c === quote) {
                state = STATE.NORMAL;
                out += ' ';
                i += 1;
                continue;
            }
            out += ' ';
            i += 1;
            continue;
        }

        if (state === STATE.TRIPLE_SINGLE || state === STATE.TRIPLE_DOUBLE) {
            const q = state === STATE.TRIPLE_SINGLE ? "'" : '"';
            if (c === '\\') {
                out += '  ';
                i += 2;
                continue;
            }
            if (c === q && c2 === q && c3 === q) {
                state = STATE.NORMAL;
                out += '   ';
                i += 3;
                continue;
            }
            out += c === '\n' ? '\n' : ' ';
            i += 1;
            continue;
        }

        /* Unreachable. */
        out += c;
        i += 1;
    }

    return out;
}

/* ------------------------------------------------------------------ */
/* Construct extractors — each captures a DECLARED NAME, nothing else. */
/* Keyword literals are matched WITHOUT the `i` flag: language keywords */
/* are fixed-case, and case-insensitive keyword matching is what let    */
/* prose like "This class handles PDF export" match `class` via         */
/* "...handles PDF...". Only the captured name is compared to the       */
/* capability pattern case-insensitively.                                */
/* ------------------------------------------------------------------ */

const CONSTRUCTS = [
    // JavaScript / TypeScript
    { lang: 'javascript', kind: 'function declaration', re: /\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/ },
    { lang: 'javascript', kind: 'arrow function assignment', re: /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>/ },
    { lang: 'javascript', kind: 'class declaration', re: /\bclass\s+([A-Za-z_$][\w$]*)/ },
    // Dotted-chain property assignment: `util.pdfExport = function(...) {}`,
    // `handlers.pdf.export = () => {}` — captures the last segment of the chain.
    { lang: 'javascript', kind: 'property chain assignment', re: /\b(?:[A-Za-z_$][\w$]*\.)+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)/ },
    // Object / map property or method definitions: `pdfExport: () => {}`,
    // `"pdf-export": function() {}` — common for capability handler
    // registries keyed by name. Deliberately narrow: the value must
    // itself be a function or arrow function. A bare value (`pdf: true`,
    // `pdf: null`, `pdf: "x"`) is a config flag, not implementation, and
    // a nested object (`pdf: { enabled: true }`) is still just config —
    // neither may match here.
    { lang: 'javascript', kind: 'object property/method', re: /^\s*["'`]?([A-Za-z_$][\w$]*)["'`]?\s*:\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)/ },
    { lang: 'javascript', kind: 'object shorthand method', re: /^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/ },

    // Python
    { lang: 'python', kind: 'async function definition', re: /\basync\s+def\s+([A-Za-z_]\w*)\s*\(/ },
    { lang: 'python', kind: 'function definition', re: /\bdef\s+([A-Za-z_]\w*)\s*\(/ },
    { lang: 'python', kind: 'class definition', re: /\bclass\s+([A-Za-z_]\w*)/ },
    { lang: 'python', kind: 'assignment', re: /^\s*(?!if\b|elif\b|while\b|for\b|return\b|assert\b)([A-Za-z_]\w*)\s*=(?!=)(?!>)\s*\S/ },

    // Go
    { lang: 'go', kind: 'function declaration', re: /\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(/ },
    { lang: 'go', kind: 'struct declaration', re: /\btype\s+([A-Za-z_]\w*)\s+struct\s*\{/ },
    { lang: 'go', kind: 'short variable declaration', re: /\b([A-Za-z_]\w*)\s*:=/ },
    { lang: 'go', kind: 'var declaration', re: /\bvar\s+([A-Za-z_]\w*)\b/ },

    // Rust
    { lang: 'rust', kind: 'function declaration', re: /\b(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*\(/ },
    { lang: 'rust', kind: 'struct declaration', re: /\b(?:pub\s+)?struct\s+([A-Za-z_]\w*)/ },
    { lang: 'rust', kind: 'impl block', re: /\bimpl(?:<[^>]+>)?\s+([A-Za-z_]\w*)/ },
    { lang: 'rust', kind: 'let binding', re: /\blet\s+(?:mut\s+)?([A-Za-z_]\w*)\s*=/ },

    // Java (requires a visibility/other modifier to bound the false-positive
    // rate; package-private methods without one are a documented gap)
    { lang: 'java', kind: 'method declaration', re: /\b(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:[\w<>\[\],.\s]+?)\s+([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:throws\s+[\w,.\s]+)?\s*\{/ },
    { lang: 'java', kind: 'class declaration', re: /\b(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+([A-Za-z_]\w*)/ },

    // C#
    { lang: 'csharp', kind: 'method declaration', re: /\b(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:override\s+)?(?:[\w<>\[\],.\s]+?)\s+([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{/ },
    { lang: 'csharp', kind: 'class declaration', re: /\b(?:public\s+)?(?:abstract\s+)?(?:sealed\s+)?class\s+([A-Za-z_]\w*)/ },

    // Kotlin
    { lang: 'kotlin', kind: 'function declaration', re: /\bfun\s+(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)\s*\(/ },
    { lang: 'kotlin', kind: 'class declaration', re: /\bclass\s+([A-Za-z_]\w*)/ },

    // PHP
    { lang: 'php', kind: 'function declaration', re: /\bfunction\s+([A-Za-z_]\w*)\s*\(/ },
    { lang: 'php', kind: 'class declaration', re: /\bclass\s+([A-Za-z_]\w*)/ },
    { lang: 'php', kind: 'variable assignment', re: /\$([A-Za-z_]\w*)\s*=(?!=)(?!>)\s*\S/ },

    // Ruby
    { lang: 'ruby', kind: 'method definition', re: /\bdef\s+(?:self\.)?([A-Za-z_][\w?!]*)/ },
    { lang: 'ruby', kind: 'class definition', re: /\bclass\s+([A-Za-z_]\w*)/ },
];

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

/**
 * Does this single line of (already comment/string-stripped, or raw —
 * this function strips it itself) source contain implementation evidence
 * for the capability described by `patterns`?
 *
 * Fixes, relative to the original pasted version:
 *   1. Every construct now captures the DECLARED NAME and tests the
 *      capability pattern against that name only, not "does the
 *      capability word appear anywhere on the line".
 *   2. Keyword regexes no longer carry the `i` flag.
 *   3. The generic `\b[A-Za-z_][\w]*\s*=\s*` fallback (matched `==`,
 *      `>=`, `=>`) is gone, replaced with per-language assignment
 *      extractors that exclude comparison/arrow operators.
 *   4. `buildCapabilityIdentifierPattern` joins tokens in order instead
 *      of OR-ing them, and is only ever tested against a captured name.
 */
function looksLikeImplementation(line, patterns) {
    const cleaned = stripCommentsAndStrings(line);

    if (!containsCapabilityToken(cleaned, patterns)) {
        return false;
    }

    const identifierPattern = buildCapabilityIdentifierPattern(patterns);
    if (!identifierPattern) {
        return false;
    }

    for (const construct of CONSTRUCTS) {
        const match = construct.re.exec(cleaned);
        if (match && match[1] && identifierPattern.test(match[1])) {
            return true;
        }
    }

    return false;
}

/**
 * Join physically-wrapped declarations (parameter lists split across
 * lines) into logical lines before matching, and strip comments/strings
 * across the WHOLE source first so multi-line block comments and
 * triple-quoted strings are handled correctly (a per-line stripper can't
 * see that a `/*` opened three lines up).
 *
 * Returns an array of { lineNumber, logicalLine, matched } — lineNumber
 * is the first physical line of the logical line, 1-indexed.
 */
function scanSource(source, patterns) {
    const cleaned = stripCommentsAndStrings(source);
    const physicalLines = cleaned.split('\n');
    const results = [];

    const MAX_JOIN = 10;
    let i = 0;
    while (i < physicalLines.length) {
        let logical = physicalLines[i];
        let balance = parenBalance(logical);
        let joined = 0;
        let j = i;
        while (balance > 0 && joined < MAX_JOIN && j + 1 < physicalLines.length) {
            j += 1;
            logical += ' ' + physicalLines[j];
            balance += parenBalance(physicalLines[j]);
            joined += 1;
        }

        results.push({
            lineNumber: i + 1,
            logicalLine: logical,
            matched: looksLikeImplementation(logical, patterns),
        });

        i = j + 1;
    }

    return results;
}

function parenBalance(line) {
    let balance = 0;
    for (const ch of line) {
        if (ch === '(') balance += 1;
        else if (ch === ')') balance -= 1;
    }
    return balance;
}

module.exports = {
    SUPPORTED_LANGUAGES,
    UNSUPPORTED_LANGUAGES,
    tokensForCapabilityName,
    patternsForCapabilityName,
    containsCapabilityToken,
    buildCapabilityIdentifierPattern,
    stripCommentsAndStrings,
    looksLikeImplementation,
    scanSource,
    CONSTRUCTS,
};
