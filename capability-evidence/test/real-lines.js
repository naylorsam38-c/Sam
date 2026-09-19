'use strict';

/*
 * Real-repo evidence, gathered via GitHub code search (mcp__github__search_code)
 * on 2026-09-19. Every line below is transcribed verbatim from that search's
 * `text_matches[].fragment` output — nothing here is synthesised. Each entry
 * records the repository, file path and blob sha GitHub returned, so any line
 * can be re-verified against the live repo.
 *
 * ---------------------------------------------------------------------
 * CONFIG — change these if Sam wants different capability names tested.
 * Each is turned into a `patterns` array via patternsForCapabilityName().
 * ---------------------------------------------------------------------
 */
const CAPABILITY_PDF_EXPORT = 'PDF Export';   // the capability name used in Sam's own pasted comments/examples
const CAPABILITY_EXPORT_DATA = 'export data'; // capability #13 in Sam's 81-name list (job 1)

module.exports = {
    /* ---------------- DEFECT 1 ----------------
     * "Token must be in the name" only applied at the end — the first nine
     * checks returned true if the capability word appeared ANYWHERE on the
     * line, not in the declared name.
     */
    defect1: [
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'function export_code(pdf) {',
            provenance: {
                repo: 'pelinquin/ConnectedGraph',
                path: 'cg.js',
                sha: 'c358c0cf27d5e32eec880775fd04aa25638c4cb9',
            },
            note: 'Declared name is "export_code" (an SVG/code exporter) — "pdf" only appears as an unrelated parameter name on the same line. Old code sees the "function" keyword + "pdf" and "export" anywhere on the line and returns true regardless.',
            expectOld: true,
            expectNew: false,
        },
    ],

    /* ---------------- DEFECT 2 ----------------
     * The `i` flag lets English prose/identifiers match keyword regexes
     * regardless of case. Isolated at the regex level (not run through the
     * full comment stripper) so the case-sensitivity fix is shown on its
     * own, independent of the comment-stripping fix.
     */
    defect2: [
        {
            rawFragment: '// Class is exported (eslint flag)',
            provenance: {
                repo: 'CodingTrain/Flappy-Bird-Clone',
                path: 'bird.js',
                sha: '420c09c0b59b8925d81aab544d505220f7cb9985',
            },
            note: 'A real comment. "Class" (capitalised, not the keyword) is followed by "is" — matches \\bclass\\s+[A-Za-z_$][\\w$]* only because of the /i flag. With the flag removed, the literal lowercase keyword "class" is required and this text no longer matches.',
        },
    ],

    /* ---------------- DEFECT 3 ----------------
     * The generic `\b[A-Za-z_][\w]*\s*=\s*` fallback (meant to catch
     * Python/Go/Rust-style handler assignments) also matches `==`, `>=`,
     * `=>` because it only requires ONE `=` character after the identifier.
     */
    defect3: [
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'if(config.format == "pdf") {',
            provenance: {
                repo: 'magicbookproject/magicbook',
                path: 'src/plugins/pdf.js',
                sha: '1b18707106f2d1c01acbbef81784ce6a14bb516e',
            },
            note: 'A plain equality check on a config value. Old code\'s generic `=` fallback matches the first `=` of `==`, and the OR-joined capability pattern matches "pdf" inside the string literal, so it is wrongly counted as PDF-export implementation evidence.',
            expectOld: true,
            expectNew: false,
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'if ( format == "pdf" || format == "csv" )',
            provenance: {
                repo: 'reportico-web/reportico',
                path: 'assets/js/reportico.js',
                sha: '1ee3a05e557096b6efe2062f8fa20f3bd148cc60',
            },
            note: 'Same defect, second repo, corroborating.',
            expectOld: true,
            expectNew: false,
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: '} else if (format == "pdf") {',
            provenance: {
                repo: 'LivelyKernel/lively4-core',
                path: 'src/components/tools/lively-container.js',
                sha: 'df7408b2e144a5c55119783f8680509d277901e7',
            },
            note: 'Same defect, third repo, corroborating.',
            expectOld: true,
            expectNew: false,
        },
    ],

    /* ---------------- DEFECT 4 ----------------
     * buildCapabilityIdentifierPattern ORs the capability's tokens instead
     * of joining them — a single-token match (e.g. "export" alone) is
     * enough to count as evidence for a two-word capability like "PDF
     * Export".
     */
    defect4: [
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'async function export_nominees() {',
            provenance: {
                repo: 'mainy1995/MemeHub-Bot',
                path: 'mha.js',
                sha: 'a8201d5a6a40fb0c635f3aaf9efeb65d3dc4a07c',
            },
            note: 'Declared name "export_nominees" has nothing to do with PDF export — it exports a list of awards nominees. The old OR-joined pattern (pdf|export) matches on "export" alone.',
            expectOld: true,
            expectNew: false,
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'function export_data(captions) {',
            provenance: {
                repo: 'machineonamission/aidatasetfromvideo',
                path: 'app.js',
                sha: '423c0f44900010464cbfbc2313a122e2cdf50fed',
            },
            note: 'Same defect, second repo, corroborating.',
            expectOld: true,
            expectNew: false,
        },
        {
            /* Direct unit-level isolation of the OR-vs-AND join itself,
             * independent of any other fix, against a captured name from a
             * real repo. */
            capturedName: 'export_nominees',
            note: 'buildCapabilityIdentifierPattern(patterns) tested directly against a real captured identifier.',
        },
    ],

    /* ---------------- TRUE POSITIVES ----------------
     * Real declarations whose names genuinely carry the capability — must
     * still match after the fix, across multiple languages/styles.
     */
    truePositives: [
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'class PDFExport {',
            provenance: { repo: 'WebbyLab/js-html-to-pdf', path: 'PDFExport.js', sha: '5c6e2c4f085f468aa68171521f0ff027eeeb3ce9' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'class PDFExport {',
            provenance: { repo: 'SHYMOM/Mess-Manager', path: 'js/pdf.js', sha: 'a30308bdd12e83baaeedd0cfd96cd871bdce9db7' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'export async function pdfExport(options) {',
            provenance: { repo: 'cytoscape/cytoscape.js-pdf-export', path: 'src/pdf-export.js', sha: 'a63d7ed13cd5a98ef88b178377d6452dd8374e6b' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'export async function pdfExport (options = {}) {',
            provenance: { repo: 'autotelic/fastify-pdf-export', path: 'index.js', sha: 'ea825664ab16d210fe0659f53773de8462b56c1b' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'export default function PdfExport({ cardRef }) {',
            provenance: { repo: 'Reapercake/questforge-pwa', path: 'src/PdfExport.js', sha: '491668de5100af7c19e68b4f50be0381c52c6ce9' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'function PDFExport() {',
            provenance: { repo: 'recordins/recordin-EthereumJ-2018', path: 'www/js/navbar.js', sha: '9c400b5a4cb164b2f5998f022a087898dd9b54cc' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'export const PDFExport = ({ student, onClose }) => {',
            provenance: { repo: 'quinnmcquade/HistoricalFictionHistoryFair', path: 'src/PDFExport.jsx', sha: 'f029a01cf4a39dcf02dc0cec6ec864b14605198c' },
        },
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: 'util.pdfExport = function(dom = null, name) {',
            provenance: { repo: 'Kelichao/vue.js.2.0', path: 'src/js/util.js', sha: '36d337190c249f1ad8678b41fc3272b25ff16a33' },
        },
        /* Non-JS language coverage, added to prove the extended construct
         * list (Python/Go/Rust/Java) works on real code, not just JS. */
        {
            capability: 'Export Report',
            line: 'def export_report(df, kpis, okrs, ia_analysis):',
            provenance: { repo: 'grisuno/LazyOwn', path: 'report.py', sha: '469f889b3e519ce979673f365b049ddda52d715f' },
        },
        {
            capability: 'Export PDF',
            line: 'func ExportPDF(sess *session.Session, outputPath string) error {',
            provenance: { repo: 'KKingZero/Zypheron-CLI', path: 'zypheron-go/internal/reports/formats.go', sha: 'c4c27abb9c8e4833f886008003391a26f735d592' },
        },
        {
            capability: 'Export PDF',
            line: 'pub fn export_pdf(path: impl AsRef<Path>, input: impl Into<ExportInput>) -> Result<(), Error> {',
            provenance: { repo: 'fastrepl/anarlog', path: 'crates/export-core/src/export.rs', sha: '90a3c91b4de9aeba832ac2ea07496d89e91c6aad' },
        },
        {
            capability: 'Export PDF',
            line: 'public void exportPdf(ExportConfigure config) {',
            provenance: { repo: 'youseries/ureport', path: 'ureport2-core/src/main/java/com/bstek/ureport/export/ExportManagerImpl.java', sha: '5ca9377e7345fba2ed9684f6fc5e2ea0984afa69' },
        },
    ],

    /* ---------------- TRUE NEGATIVE CONTROL ----------------
     * A capability word inside a doc comment, with no declaration on the
     * line at all. Both old and new code should agree: false.
     */
    trueNegatives: [
        {
            capability: CAPABILITY_PDF_EXPORT,
            line: ' *   @file pdfExport.js',
            provenance: { repo: 'HashDefineElectronics/KiCad_BOM_Wizard', path: 'Lib/pdfExport.js', sha: '01c57e11cb6912617b2f474e1c04972dc0fe10c8' },
        },
    ],

    /* ---------------- ADVERSARIAL: config flags are not implementation ----------------
     * Found by deliberately trying to break the new "object property"
     * construct after it was added (it is not one of the four original
     * defects — it's new code we wrote, so we stress-tested it the same
     * way). A bare or nested-object value for a capability-named key is
     * config, not implementation evidence, and must not match.
     */
    adversarial: [
        { capability: 'pdf', line: '  pdf: true,', expect: false, note: 'boolean config flag' },
        { capability: 'pdf', line: '  pdf: null,', expect: false, note: 'null config flag' },
        { capability: 'pdf', line: '  pdf: { enabled: true },', expect: false, note: 'nested config object, not a handler' },
        { capability: 'pdf', line: '  pdf: () => registerPdfHandler(),', expect: true, note: 'arrow function value — genuine handler wiring, must still match' },
    ],

    CAPABILITY_PDF_EXPORT,
    CAPABILITY_EXPORT_DATA,
};
