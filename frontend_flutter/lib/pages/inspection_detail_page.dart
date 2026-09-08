import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:universal_html/html.dart' as html;
import '../core/api_client.dart';
import '../core/theme.dart';
import '../widgets/authorized_image.dart';
import '../widgets/inspection_workflow_stepper.dart';
import '../widgets/inspection_ocr_summary_section.dart';
import '../widgets/ocr_bounding_box_canvas.dart';
import '../widgets/ocr_block_table.dart';
import '../widgets/extracted_declarations_section.dart';
import '../widgets/context_applicability_section.dart';
import '../widgets/rule_compliance_section.dart';
import '../widgets/human_review_section.dart';
import '../widgets/report_export_section.dart';
import '../widgets/audit_trail_viewer.dart';

class InspectionDetailPage extends StatefulWidget {
  final String id;

  const InspectionDetailPage({super.key, required this.id});

  @override
  State<InspectionDetailPage> createState() => _InspectionDetailPageState();
}

class _InspectionDetailPageState extends State<InspectionDetailPage> {
  Map<String, dynamic>? _inspection;
  Map<String, dynamic>? _ocrSummary;
  Map<String, dynamic>? _evaluation;
  Map<String, dynamic>? _reportSummary;
  bool _loading = true;
  String? _error;
  bool _runningAnalysis = false;
  Map<String, dynamic>? _selectedImageForModal;
  String _modalViewMode = 'ocr-boxes'; // ocr-boxes, side-by-side, original, preprocessed
  List<OCRBlockData> _selectedImageBlocks = [];
  bool _loadingModalBlocks = false;
  String? _selectedBlockId;
  List<Map<String, dynamic>> _colorMarks = [];

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() => _loading = true);
    try {
      final iRes = await ApiClient().get('/inspections/${widget.id}');
      Map<String, dynamic>? sRes;
      try {
        final rawSummary = await ApiClient().get('/inspections/${widget.id}/ocr/summary');
        if (rawSummary is Map<String, dynamic>) sRes = rawSummary;
      } catch (_) {}

      Map<String, dynamic>? eRes;
      try {
        final rawEval = await ApiClient().get('/inspections/${widget.id}/evaluation');
        if (rawEval is Map<String, dynamic>) eRes = rawEval;
      } catch (_) {}

      Map<String, dynamic>? rRes;
      try {
        final rawRep = await ApiClient().get('/inspections/${widget.id}/reports/summary');
        if (rawRep is Map<String, dynamic>) rRes = rawRep;
      } catch (_) {}

      List<Map<String, dynamic>> cMarks = [];
      try {
        final cRes = await ApiClient().get('/inspections/${widget.id}/color-marks');
        if (cRes is Map<String, dynamic> && cRes['detected_color_marks'] is List) {
          cMarks = (cRes['detected_color_marks'] as List).map((e) => e as Map<String, dynamic>).toList();
        }
      } catch (_) {}

      if (mounted) {
        setState(() {
          _inspection = iRes is Map<String, dynamic> ? iRes : null;
          _ocrSummary = sRes;
          _evaluation = eRes;
          _reportSummary = rRes;
          _colorMarks = cMarks;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to load inspection details.';
          _loading = false;
        });
      }
    }
  }

  Future<void> _runAnalysis() async {
    setState(() => _runningAnalysis = true);
    try {
      await ApiClient().post('/inspections/${widget.id}/analysis', timeout: const Duration(minutes: 5));
      await _fetch();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Automated compliance analysis completed!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Analysis error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _runningAnalysis = false);
    }
  }

  Future<void> _downloadPdf() async {
    try {
      final code = _inspection?['inspection_code'] ?? 'case';
      final bytes = await ApiClient().getBytes('/inspections/${widget.id}/reports/pdf');
      if (kIsWeb) {
        final blob = html.Blob([bytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        html.AnchorElement(href: url)
          ..setAttribute('download', 'LabelSure_Statutory_Report_$code.pdf')
          ..click();
        html.Url.revokeObjectUrl(url);
      }
    } catch (_) {}
  }

  Future<void> _openImageModal(Map<String, dynamic> img) async {
    setState(() {
      _selectedImageForModal = img;
      _modalViewMode = 'ocr-boxes';
      _loadingModalBlocks = true;
      _selectedImageBlocks = [];
    });

    try {
      final ocrRes = await ApiClient().get('/inspections/${widget.id}/images/${img['id']}/ocr');
      if (ocrRes is Map<String, dynamic> && ocrRes['blocks'] is List) {
        final blocksList = (ocrRes['blocks'] as List).asMap().entries.map((e) {
          return OCRBlockData.fromJson(e.value as Map<String, dynamic>, e.key);
        }).toList();

        if (mounted) {
          setState(() {
            _selectedImageBlocks = blocksList;
            _loadingModalBlocks = false;
          });
        }
      }
    } catch (_) {
      if (mounted) setState(() => _loadingModalBlocks = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const SizedBox(
        height: 400,
        child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
      );
    }

    if (_error != null || _inspection == null) {
      return Center(
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: AppTheme.glassPanel(),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.rose, size: 48),
              const SizedBox(height: 12),
              Text(_error ?? 'Inspection record not found.', style: const TextStyle(color: Colors.white, fontSize: 14)),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.go('/inspections'),
                child: const Text('← Return to Inspections'),
              ),
            ],
          ),
        ),
      );
    }

    final insp = _inspection!;
    final status = insp['status']?.toString() ?? 'DRAFT';
    final isCompliant = status == 'COMPLIANT';
    final isNonCompliant = status == 'NON_COMPLIANT';
    final images = (insp['images'] as List?) ?? [];
    final justifications = _getGuidelineFailureJustifications();

    return Stack(
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Executive Direct Verdict Banner
            _buildVerdictBanner(status, isCompliant, isNonCompliant),
            const SizedBox(height: 20),

            // Statutory Guideline Failure Justifications Banner
            if (justifications.isNotEmpty) ...[
              _buildGuidelineFailureJustificationsBanner(justifications),
              const SizedBox(height: 20),
            ],

            // Header Section
            _buildHeaderSection(insp),
            const SizedBox(height: 20),

            // 14-Step Workflow Stepper Bar
            InspectionWorkflowStepper(
              inspection: insp,
              ocrSummary: _ocrSummary,
              hasQuality: images.any((img) => img['processing_result']?['quality_status'] != null),
              hasExtraction: (insp['declarations_count'] ?? 0) > 0,
              hasContext: insp['context_resolved'] == true,
              hasEvaluation: (insp['evaluations_count'] ?? 0) > 0,
              hasReview: insp['review_status'] != null,
              onRunOCR: () => ApiClient().post('/inspections/${widget.id}/ocr').then((_) => _fetch()),
              onExtract: _runAnalysis,
            ),
            const SizedBox(height: 24),

            // Main 2-column layout: Context Specs + Evidence Photos / Pipeline info
            LayoutBuilder(
              builder: (context, constraints) {
                final isDesktop = constraints.maxWidth >= 960;
                if (isDesktop) {
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 2,
                        child: Column(
                          children: [
                            _buildProductSpecsCard(insp),
                            const SizedBox(height: 20),
                            _buildEvidenceGalleryCard(images),
                          ],
                        ),
                      ),
                      const SizedBox(width: 20),
                      Expanded(
                        flex: 1,
                        child: _buildRightSideInfoCard(insp),
                      ),
                    ],
                  );
                }
                return Column(
                  children: [
                    _buildProductSpecsCard(insp),
                    const SizedBox(height: 20),
                    _buildEvidenceGalleryCard(images),
                    const SizedBox(height: 20),
                    _buildRightSideInfoCard(insp),
                  ],
                );
              },
            ),
            const SizedBox(height: 24),

            // Extracted OCR Evidence Summary Across Panels
            InspectionOCRSummarySection(
              summary: _ocrSummary,
              canEdit: true,
              onTriggerBatchOCR: () async {
                await ApiClient().post('/inspections/${widget.id}/ocr');
                _fetch();
              },
              onOpenImageModal: (imgId) {
                final target = images.firstWhere((i) => i['id'] == imgId, orElse: () => null);
                if (target != null) _openImageModal(target);
              },
            ),
            const SizedBox(height: 24),

            // Extracted Declarations Table
            ExtractedDeclarationsSection(
              inspection: insp,
              onExtractionComplete: _fetch,
            ),
            const SizedBox(height: 24),

            // Context & Applicability Section
            ContextApplicabilitySection(inspection: insp),
            const SizedBox(height: 24),

            // Rule Compliance Evaluation
            RuleComplianceSection(
              inspection: insp,
              onEvaluationComplete: _fetch,
            ),
            const SizedBox(height: 24),

            // Human Review Adjudication
            HumanReviewSection(
              inspection: insp,
              onReviewUpdated: _fetch,
            ),
            const SizedBox(height: 24),

            // Report Export & Downloads
            ReportExportSection(inspection: insp),
            const SizedBox(height: 24),

            // Audit Trail
            AuditTrailViewerWidget(inspection: insp),
            const SizedBox(height: 32),
          ],
        ),

        // Interactive OCR Bounding Box & Evidence Modal Dialog
        if (_selectedImageForModal != null) _buildImageInspectionModal(),
      ],
    );
  }

  Widget _buildVerdictBanner(String status, bool isCompliant, bool isNonCompliant) {
    Color bannerGradStart = isCompliant
        ? const Color(0xFF064E3B)
        : isNonCompliant
            ? const Color(0xFF881337)
            : const Color(0xFF78350F);

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [bannerGradStart, const Color(0xFF0F172A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isCompliant
              ? AppTheme.emerald
              : isNonCompliant
                  ? AppTheme.rose
                  : AppTheme.amber,
        ),
        boxShadow: const [
          BoxShadow(color: Color(0x66000000), blurRadius: 20, offset: Offset(0, 8)),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: isCompliant
                            ? AppTheme.emerald
                            : isNonCompliant
                                ? AppTheme.rose
                                : AppTheme.amber,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        isCompliant
                            ? '✓ PASS — COMPLIANT'
                            : isNonCompliant
                                ? '✕ FAIL — NON-COMPLIANT'
                                : '⚠ ATTENTION — REVIEW REQUIRED',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.black),
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text('LMPC Rules 2011-2026 Statutory Status',
                        style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8), fontFamily: 'monospace')),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  '${_inspection!['inspection_code']} · ${_inspection!['product_name'] ?? 'Packaged Commodity'}',
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Automated Legal Metrology Pipeline Completed (OCR Panel Processing → Declaration Extraction → Rule Evaluation).',
                  style: TextStyle(fontSize: 12, color: Color(0xFFCBD5E1)),
                ),
              ],
            ),
          ),
          const SizedBox(width: 20),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                icon: const Icon(Icons.picture_as_pdf, size: 16),
                label: const Text('Download Official PDF Report', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                onPressed: _downloadPdf,
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                icon: _runningAnalysis
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.refresh, size: 16),
                label: Text(_runningAnalysis ? 'Running…' : '⚡ Re-Run Auto-Analysis', style: const TextStyle(fontSize: 11)),
                onPressed: _runningAnalysis ? null : _runAnalysis,
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<String> _getGuidelineFailureJustifications() {
    if (_evaluation != null && _evaluation!['guideline_failure_justifications'] is List) {
      final list = (_evaluation!['guideline_failure_justifications'] as List).map((e) => e.toString()).toList();
      if (list.isNotEmpty) return list;
    }
    if (_reportSummary != null && _reportSummary!['guideline_failure_justifications'] is List) {
      final list = (_reportSummary!['guideline_failure_justifications'] as List).map((e) => e.toString()).toList();
      if (list.isNotEmpty) return list;
    }
    return [];
  }

  Widget _buildGuidelineFailureJustificationsBanner(List<String> justifications) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E1014),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0x80F43F5E), width: 1.5),
        boxShadow: const [
          BoxShadow(
            color: Color(0x33F43F5E),
            blurRadius: 20,
            offset: Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0x33F43F5E),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.warning_amber_rounded, color: AppTheme.rose, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'Legal Metrology Guideline Failure Justifications',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Statutory non-compliance justifications under PCR Rule 6(1) & Legal Metrology Act, 2009',
                        style: TextStyle(fontSize: 11, color: Color(0xFFCBD5E1)),
                      ),
                    ],
                  ),
                ],
              ),
              Wrap(
                spacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0x33F43F5E),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: const Color(0x66F43F5E)),
                    ),
                    child: Text(
                      '${justifications.length} VIOLATIONS IDENTIFIED',
                      style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.rose, fontFamily: 'monospace'),
                    ),
                  ),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFFECDD3),
                      side: const BorderSide(color: Color(0x66F43F5E)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    icon: const Icon(Icons.copy, size: 13),
                    label: const Text('Copy All Justifications', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    onPressed: () {
                      final text = "Legal Metrology Guideline Failure Justifications\n${justifications.join('\n')}";
                      Clipboard.setData(ClipboardData(text: text));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Copied Legal Metrology Guideline Failure Justifications to clipboard')),
                      );
                    },
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: justifications.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final item = justifications[index];
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0x66F43F5E)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 2, right: 8),
                      child: Icon(Icons.error_outline, size: 14, color: AppTheme.rose),
                    ),
                    Expanded(
                      child: SelectableText(
                        item,
                        style: const TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: Color(0xFFFECDD3),
                          height: 1.45,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 14, color: Color(0xFFFDA4AF)),
                      tooltip: 'Copy justification',
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: item));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Copied violation justification to clipboard')),
                        );
                      },
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderSection(Map<String, dynamic> insp) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                InkWell(
                  onTap: () => context.go('/inspections'),
                  child: const Text('← All Inspections', style: TextStyle(fontSize: 11, color: AppTheme.emerald, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 6),
                const Text('/', style: TextStyle(color: Color(0xFF475569))),
                const SizedBox(width: 6),
                Text(insp['id']?.toString().substring(0, 8) ?? '',
                    style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF64748B))),
              ],
            ),
            const SizedBox(height: 6),
            Text(insp['inspection_code']?.toString() ?? '',
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 2),
            Text(
              'Created by ${insp['created_by_name'] ?? 'Inspector'} on ${insp['created_at'] != null ? DateFormat.yMMMd().add_jm().format(DateTime.tryParse(insp['created_at']) ?? DateTime.now()) : '—'}',
              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
            ),
          ],
        ),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.emerald,
            foregroundColor: const Color(0xFF090D16),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          ),
          icon: const Icon(Icons.bolt, size: 16),
          label: const Text('⚡ Auto-Analyze Package', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
          onPressed: _runAnalysis,
        ),
      ],
    );
  }

  Widget _buildProductSpecsCard(Map<String, dynamic> insp) {
    final banInfo = insp['international_ban_info'] as Map<String, dynamic>?;

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('PRODUCT & DECLARATION CONTEXT',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
          const Divider(color: Color(0xFF1E293B), height: 20),
          Wrap(
            spacing: 24,
            runSpacing: 16,
            children: [
              _buildSpecField('Product Name', insp['product_name'] ?? '—', isHighlight: true),
              _buildSpecField('Brand Name', insp['brand_name'] ?? '—', isHighlight: true),
              _buildSpecField('Category', insp['category'] ?? '—'),
              _buildSpecField('Package Type', insp['package_type'] ?? '—'),
              _buildSpecField('Import Status', insp['import_status'] ?? 'DOMESTIC'),
              _buildSpecField('Barcode / GTIN', insp['barcode'] ?? '—'),
              _buildSpecField('Manufacturer', insp['manufacturer_name'] ?? '—'),
              _buildSpecField('Packer', insp['packer_name'] ?? '—'),
            ],
          ),
          if (banInfo != null || (insp['product_name'] != null && insp['product_name'].toString().isNotEmpty))
            _buildInternationalBanCard(banInfo, insp['product_name']?.toString()),
          _buildColorMarksCard(_colorMarks),
        ],
      ),
    );
  }

  Widget _buildInternationalBanCard(Map<String, dynamic>? banInfo, String? productName) {
    final status = banInfo?['status']?.toString() ?? 'PERMITTED';
    final isBanned = status == 'BANNED' || banInfo?['is_banned'] == true;
    final isRestricted = status == 'RESTRICTED';
    final countries = ((banInfo?['countries'] ?? banInfo?['banned_countries']) as List?)?.map((e) => e.toString()).toList() ?? [];
    final authorities = (banInfo?['authorities'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final reason = banInfo?['reason']?.toString() ??
        'Standard packaged commodity cleared under Indian Legal Metrology. No overseas bans recorded.';
    final advisory = banInfo?['advisory']?.toString() ??
        'Eligible for export subject to destination country labeling regulations.';

    final Color statusColor = isBanned
        ? AppTheme.rose
        : isRestricted
            ? AppTheme.amber
            : AppTheme.emerald;

    final Color bgColor = isBanned
        ? const Color(0xFF200F14)
        : isRestricted
            ? const Color(0xFF241C0A)
            : const Color(0xFF09231B);

    final Color borderColor = isBanned
        ? const Color(0xFFF43F5E)
        : isRestricted
            ? const Color(0xFFF59E0B)
            : const Color(0xFF10B981);

    final String badgeText = isBanned
        ? 'PROHIBITED / BANNED IN FOREIGN JURISDICTIONS'
        : isRestricted
            ? 'RESTRICTED / STRICT ALLERGEN RULES ABROAD'
            : 'GLOBALLY PERMITTED / NO EXPORT BANS RECORDED';

    return Container(
      margin: const EdgeInsets.only(top: 18),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor.withValues(alpha: 0.6), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isBanned
                    ? Icons.gavel_rounded
                    : isRestricted
                        ? Icons.warning_amber_rounded
                        : Icons.verified_user_outlined,
                color: statusColor,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'INTERNATIONAL REGULATORY STATUS: ${(productName ?? "COMMODITY").toUpperCase()}',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: statusColor,
                    letterSpacing: 0.5,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.2),
                  border: Border.all(color: statusColor.withValues(alpha: 0.8)),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  badgeText,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            reason,
            style: const TextStyle(fontSize: 11, color: Colors.white, height: 1.4),
          ),
          if (countries.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Text('Banned / Restricted In: ',
                    style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                ...countries.map((c) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                      ),
                      child: Text(c,
                          style: TextStyle(fontSize: 10, color: statusColor, fontWeight: FontWeight.w600)),
                    )),
              ],
            ),
          ],
          if (authorities.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Text('Enforcing Agencies: ',
                    style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                ...authorities.map((a) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Text(a,
                          style: const TextStyle(
                              fontSize: 9.5, color: Color(0xFFCBD5E1), fontFamily: 'monospace')),
                    )),
              ],
            ),
          ],
          const SizedBox(height: 6),
          Text(
            'Statutory Advisory: $advisory',
            style: const TextStyle(fontSize: 10.5, fontStyle: FontStyle.italic, color: Color(0xFFCBD5E1)),
          ),
        ],
      ),
    );
  }

  Widget _buildColorMarksCard(List<Map<String, dynamic>> marks) {
    if (marks.isEmpty) {
      return Container(
        margin: const EdgeInsets.only(top: 14),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: const Row(
          children: [
            Icon(Icons.palette_outlined, size: 16, color: Color(0xFF64748B)),
            SizedBox(width: 8),
            Text(
              'No statutory dietary/color marks detected on uploaded packaging panels.',
              style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
            ),
          ],
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0A101D),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF1E293B), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_outlined, color: AppTheme.emerald, size: 18),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'STATUTORY COLOR & DIETARY LABEL MARKS (FSSAI / LMPC ENFORCEMENT)',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.emerald.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.5)),
                ),
                child: Text(
                  '${marks.length} DETECTED',
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.emerald),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 10,
            children: marks.map((m) {
              final type = m['type']?.toString() ?? '';
              final colorName = m['color_name']?.toString() ?? 'GREEN';
              final title = m['title']?.toString() ?? 'Mark';
              final standard = m['statutory_standard']?.toString() ?? '';
              final desc = m['description']?.toString() ?? '';
              final conf = ((m['confidence'] as num?)?.toDouble() ?? 0.8) * 100;

              Color primaryColor = AppTheme.emerald;
              Widget markEmblem;

              if (type == 'VEGETARIAN' || colorName == 'GREEN') {
                primaryColor = AppTheme.emerald;
                markEmblem = Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    border: Border.all(color: AppTheme.emerald, width: 2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Center(
                    child: Container(
                      width: 14,
                      height: 14,
                      decoration: const BoxDecoration(
                        color: AppTheme.emerald,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              } else if (type == 'NON_VEGETARIAN' || colorName == 'RED_BROWN') {
                primaryColor = AppTheme.rose;
                markEmblem = Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    border: Border.all(color: AppTheme.rose, width: 2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Center(
                    child: Container(
                      width: 14,
                      height: 14,
                      decoration: const BoxDecoration(
                        color: AppTheme.rose,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              } else if (type == 'NUTRITIONAL_WARNING' || colorName == 'YELLOW_AMBER') {
                primaryColor = AppTheme.amber;
                markEmblem = Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    border: Border.all(color: AppTheme.amber, width: 2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Center(
                    child: Icon(Icons.warning_amber_rounded, color: AppTheme.amber, size: 18),
                  ),
                );
              } else {
                primaryColor = Colors.lightBlueAccent;
                markEmblem = Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    border: Border.all(color: Colors.lightBlueAccent, width: 2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Center(
                    child: Text('+F', style: TextStyle(color: Colors.lightBlueAccent, fontWeight: FontWeight.bold, fontSize: 11)),
                  ),
                );
              }

              return Container(
                width: 320,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: primaryColor.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: primaryColor.withValues(alpha: 0.35)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    markEmblem,
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  title,
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: primaryColor,
                                  ),
                                ),
                              ),
                              Text(
                                '${conf.toStringAsFixed(0)}% match',
                                style: TextStyle(fontSize: 10, color: primaryColor.withValues(alpha: 0.8), fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Text(
                            desc,
                            style: const TextStyle(fontSize: 10.5, color: Colors.white70, height: 1.3),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            standard,
                            style: const TextStyle(fontSize: 9.5, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSpecField(String label, String value, {bool isHighlight = false}) {
    return SizedBox(
      width: 220,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontWeight: FontWeight.bold)),
          const SizedBox(height: 3),
          Text(
            value,
            style: TextStyle(
              fontSize: isHighlight ? 13 : 11,
              fontWeight: isHighlight ? FontWeight.bold : FontWeight.normal,
              color: isHighlight ? Colors.white : const Color(0xFFCBD5E1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEvidenceGalleryCard(List<dynamic> images) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Photographic Evidence & Quality Status (${images.length})',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
              const Text('Click any image for interactive OCR bounding boxes',
                  style: TextStyle(fontSize: 10, color: Color(0xFF64748B))),
            ],
          ),
          const SizedBox(height: 14),
          if (images.isEmpty)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No evidence photos uploaded.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ),
            )
          else
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: images.map((img) {
                final proc = img['processing_result'] as Map<String, dynamic>?;
                final qStatus = proc?['quality_status']?.toString() ?? 'PENDING';
                final blur = proc?['metrics']?['blur_score'];

                Color qColor = qStatus == 'GOOD'
                    ? AppTheme.emerald
                    : qStatus == 'POOR'
                        ? AppTheme.amber
                        : const Color(0xFF94A3B8);

                return InkWell(
                  onTap: () => _openImageModal(img as Map<String, dynamic>),
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    width: 175,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF1E293B)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: SizedBox(
                            height: 120,
                            width: double.infinity,
                            child: AuthorizedImage(
                              src: '/inspections/${widget.id}/images/${img['id']}/content',
                              alt: img['original_filename']?.toString(),
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                              decoration: BoxDecoration(
                                color: qColor.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(qStatus, style: TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: qColor)),
                            ),
                            Text(img['panel_type']?.toString() ?? 'PANEL',
                                style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: AppTheme.emerald)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          img['original_filename']?.toString() ?? 'photo.jpg',
                          style: const TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.bold),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (blur != null) ...[
                          const SizedBox(height: 2),
                          Text('Focus: ${(blur as num).toStringAsFixed(0)}',
                              style: const TextStyle(fontSize: 9, color: Color(0xFF64748B), fontFamily: 'monospace')),
                        ],
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildRightSideInfoCard(Map<String, dynamic> insp) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('APEX ARCHITECTURE MANDATE',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.emerald, letterSpacing: 1)),
          const SizedBox(height: 8),
          const Text(
            '"AI OBSERVES. RULES DECIDE. EVIDENCE EXPLAINS. INSPECTORS VERIFY."',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, fontStyle: FontStyle.italic),
          ),
          const SizedBox(height: 6),
          const Text(
            'OCR models extract visible statutory declarations as evidence. They never make compliance determinations.',
            style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), height: 1.5),
          ),
          const Divider(color: Color(0xFF1E293B), height: 24),
          const Text('OPENCV QUALITY STANDARDS',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          const Text('• Blur / Focus: Laplacian variance (≥100 = sharp)', style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1))),
          const SizedBox(height: 4),
          const Text('• Brightness: Mean luminance [50–205]', style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1))),
          const SizedBox(height: 4),
          const Text('• Contrast: Std dev (≥30) distinction', style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1))),
          const SizedBox(height: 4),
          const Text('• Glare / Flash: Near-white saturation (≤8%)', style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1))),
          const Divider(color: Color(0xFF1E293B), height: 24),
          const Text('CHAIN OF CUSTODY',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          Text('Inspection ID: ${insp['id']}', style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: Color(0xFF64748B))),
          const SizedBox(height: 4),
          Text('Created: ${insp['created_at']}', style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: Color(0xFF64748B))),
        ],
      ),
    );
  }

  Widget _buildImageInspectionModal() {
    final img = _selectedImageForModal!;
    final imgId = img['id'];
    final proc = img['processing_result'] as Map<String, dynamic>?;
    final preprocessedUrl = (proc?['derived_content_url'] as String?) ??
        '/inspections/${widget.id}/images/$imgId/processed';
    final contentUrl = '/inspections/${widget.id}/images/$imgId/content';
    final modalImgSrc = _modalViewMode == 'preprocessed' ? preprocessedUrl : contentUrl;

    return Container(
      color: Colors.black87,
      child: Center(
        child: Container(
          width: 1100,
          height: 680,
          margin: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF0B132B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            children: [
              // Modal Header
              Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(
                  color: Color(0xFF0F172A),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                ),
                child: Row(
                  children: [
                    Text(img['original_filename']?.toString() ?? 'Image Detail',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0x3310B981),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text('OCR: ${_selectedImageBlocks.length} Blocks',
                          style: const TextStyle(fontSize: 10, color: AppTheme.emerald, fontWeight: FontWeight.bold)),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white, size: 20),
                      onPressed: () => setState(() => _selectedImageForModal = null),
                    ),
                  ],
                ),
              ),

              // Mode Tabs & Metrics
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: const Color(0xFF131D31),
                child: Row(
                  children: [
                    _buildModalTab('ocr-boxes', '🔍 OCR Bounding Boxes (${_selectedImageBlocks.length})'),
                    const SizedBox(width: 8),
                    _buildModalTab('original', 'Raw Evidence'),
                    if (proc?['derived_image_available'] == true) ...[
                      const SizedBox(width: 8),
                      _buildModalTab('preprocessed', 'OCR-Ready Artifact'),
                    ],
                  ],
                ),
              ),

              // Modal Canvas View
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: _loadingModalBlocks
                      ? const Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2))
                      : _modalViewMode == 'ocr-boxes'
                          ? Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // Canvas Left 7 cols
                                Expanded(
                                  flex: 7,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF0F172A),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: OCRBoundingBoxCanvas(
                                      imageUrl: '/inspections/${widget.id}/images/$imgId/content',
                                      blocks: _selectedImageBlocks,
                                      selectedBlockId: _selectedBlockId,
                                      onSelectBlock: (b) => setState(() => _selectedBlockId = b.id),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 14),

                                // Block Table Right 5 cols
                                Expanded(
                                  flex: 5,
                                  child: OCRBlockTable(
                                    blocks: _selectedImageBlocks,
                                    selectedBlockId: _selectedBlockId,
                                    onSelectBlock: (b) => setState(() => _selectedBlockId = b.id),
                                  ),
                                ),
                              ],
                            )
                          : Center(
                              child: AuthorizedImage(
                                src: modalImgSrc,
                                fit: BoxFit.contain,
                              ),
                            ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModalTab(String mode, String label) {
    final active = _modalViewMode == mode;
    return InkWell(
      onTap: () => setState(() => _modalViewMode = mode),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? const Color(0x3310B981) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: active ? AppTheme.emerald : Colors.transparent),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: active ? FontWeight.bold : FontWeight.normal,
            color: active ? AppTheme.emerald : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }
}
