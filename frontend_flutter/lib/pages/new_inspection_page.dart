import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/api_client.dart';
import '../core/theme.dart';
import '../widgets/authorized_image.dart';
import '../widgets/webcam_modal.dart';

const mandatoryDeclarations = [
  (type: 'COMMON_PRODUCT_NAME', label: 'Generic / Common Commodity Name'),
  (type: 'NET_QUANTITY', label: 'Net Quantity (Magnitude & Unit)'),
  (type: 'MAXIMUM_RETAIL_PRICE', label: 'Maximum Retail Price (MRP)'),
  (type: 'UNIT_SALE_PRICE', label: 'Unit Sale Price (USP)'),
  (type: 'MONTH_YEAR_PACKAGING', label: 'Month & Year of Packaging / Import'),
  (type: 'EXPIRY_BEST_BEFORE', label: 'Expiry / Best Before Date'),
  (type: 'MANUFACTURER_ADDRESS', label: 'Manufacturer Name & Address'),
  (type: 'PACKER_ADDRESS', label: 'Packer / Importer Name & Address'),
  (type: 'COUNTRY_OF_ORIGIN', label: 'Country of Origin'),
  (type: 'CONSUMER_CARE', label: 'Consumer Care Details'),
  (type: 'DIMENSIONS', label: 'Dimensions & Size'),
  (type: 'ECOMMERCE_DECLARATION', label: 'E-Commerce Specific Declarations'),
];

const panels = ['FRONT', 'BACK', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'DECLARATION_PANEL', 'MRP_PANEL', 'OTHER'];

class NewInspectionPage extends StatefulWidget {
  final String? draftId;

  const NewInspectionPage({super.key, this.draftId});

  @override
  State<NewInspectionPage> createState() => _NewInspectionPageState();
}

class _NewInspectionPageState extends State<NewInspectionPage> {
  Map<String, dynamic>? _inspection;
  int _step = 1;
  String? _busyMessage;
  String? _error;
  String? _notice;
  List<dynamic> _candidates = [];
  bool _scanned = false;
  bool _webcamOpen = false;

  @override
  void initState() {
    super.initState();
    if (widget.draftId != null) {
      _loadDraft(widget.draftId!);
    }
  }

  Future<void> _loadDraft(String id) async {
    setState(() => _busyMessage = 'Loading draft…');
    try {
      final data = await ApiClient().get('/inspections/$id');
      if (mounted && data is Map<String, dynamic>) {
        setState(() {
          _inspection = data;
          _busyMessage = null;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _busyMessage = null);
    }
  }

  Future<void> _refreshInspection() async {
    if (_inspection == null) return;
    final data = await ApiClient().get('/inspections/${_inspection!['id']}');
    if (mounted && data is Map<String, dynamic>) {
      setState(() => _inspection = data);
    }
  }

  Future<void> _uploadFiles(List<({String filename, Uint8List bytes, String panelType})> files) async {
    setState(() {
      _busyMessage = 'Uploading photos…';
      _error = null;
      _notice = null;
    });

    try {
      if (_inspection == null) {
        final createRes = await ApiClient().post('/inspections', body: {'product_name': 'Scanning package'});
        if (createRes is Map<String, dynamic>) {
          _inspection = createRes;
        }
      }

      final id = _inspection!['id'];
      await ApiClient().uploadFiles('/inspections/$id/images', files: files);
      await _refreshInspection();
      await _scan(id);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busyMessage = null);
    }
  }

  Future<void> _scan(String id) async {
    setState(() {
      _busyMessage = 'Scanning package text… (OCR Recognition)';
      _scanned = false;
      _candidates.clear();
    });

    try {
      await ApiClient().post('/inspections/$id/ocr', timeout: const Duration(minutes: 5));
      if (mounted) setState(() => _busyMessage = 'Extracting product details…');

      await ApiClient().post('/inspections/$id/extract-declarations');
      final declRes = await ApiClient().get('/inspections/$id/declarations?limit=1000');

      await _refreshInspection();

      if (mounted) {
        setState(() {
          _candidates = declRes is List ? declRes : [];
          _scanned = true;
          _step = 2;
          _notice = _candidates.isNotEmpty
              ? 'Scan complete. Review extracted statutory declarations below.'
              : 'Text was scanned, but no supported details were identified.';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Scan failed: $e');
    } finally {
      if (mounted) setState(() => _busyMessage = null);
    }
  }

  Future<void> _submitAndAnalyze() async {
    if (_inspection == null) return;
    final id = _inspection!['id'];

    setState(() => _busyMessage = 'Submitting inspection…');
    try {
      await ApiClient().post('/inspections/$id/submit');

      setState(() => _busyMessage = 'Running automated Legal Metrology compliance analysis…');
      await ApiClient().post('/inspections/$id/analysis', timeout: const Duration(minutes: 5));

      if (mounted) {
        context.go('/inspections/$id');
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Submission or analysis error: $e');
    } finally {
      if (mounted) setState(() => _busyMessage = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final images = (_inspection?['images'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Stepper Title
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('New Packaged Commodity Inspection',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 2),
                Text(
                  _inspection != null
                      ? '${_inspection!['inspection_code']} · Draft saved'
                      : 'Capture package photos to extract mandatory LMPC declarations.',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
            Row(
              children: [
                _buildStepBadge(1, '1. Capture photos', _step == 1),
                const SizedBox(width: 8),
                _buildStepBadge(2, '2. Review & submit', _step == 2),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Progress or Error Banners
        if (_busyMessage != null) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0x3310B981),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.emerald),
            ),
            child: Row(
              children: [
                const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.emerald)),
                const SizedBox(width: 10),
                Text(_busyMessage!, style: const TextStyle(fontSize: 11, color: AppTheme.emerald, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],

        if (_error != null) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0x33F43F5E),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.rose),
            ),
            child: Text(_error!, style: const TextStyle(fontSize: 11, color: Color(0xFFFECDD3))),
          ),
          const SizedBox(height: 14),
        ],

        if (_notice != null) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0x33F59E0B),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.amber),
            ),
            child: Text(_notice!, style: const TextStyle(fontSize: 11, color: Color(0xFFFEF3C7))),
          ),
          const SizedBox(height: 14),
        ],

        if (_webcamOpen)
          WebcamModal(
            onClose: () => setState(() => _webcamOpen = false),
            onCapture: (name, bytes, panel) {
              _uploadFiles([(filename: name, bytes: bytes, panelType: panel)]);
            },
          ),

        // Step 1: Photos Capture
        if (_step == 1) _buildStep1Photos(images) else _buildStep2Review(images),
      ],
    );
  }

  Widget _buildStepBadge(int stepNum, String title, bool active) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: active ? AppTheme.emerald : const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: active ? const Color(0xFF090D16) : const Color(0xFF94A3B8),
        ),
      ),
    );
  }

  Widget _buildStep1Photos(List<dynamic> images) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Center(
            child: Text(
              'Start with Package Evidence Photos',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ),
          const SizedBox(height: 4),
          const Center(
            child: Text(
              'Photograph the commodity packaging or upload label images. PaddleOCR will scan all text and extract Rule 6 declarations.',
              style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 20),

          // Upload Area Box
          Container(
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155), style: BorderStyle.solid),
            ),
            child: Column(
              children: [
                const Icon(Icons.cloud_upload_outlined, size: 48, color: AppTheme.emerald),
                const SizedBox(height: 12),
                const Text('Choose package photos to upload',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 4),
                const Text('Supports JPEG, PNG, WEBP up to 20MB per photo',
                    style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.emerald,
                        foregroundColor: const Color(0xFF090D16),
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      icon: const Icon(Icons.photo_library, size: 16),
                      label: const Text('Browse Files', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                      onPressed: () async {
                        final files = await FilePicker.pickFiles(
                          type: FileType.image,
                        );
                        if (files.isNotEmpty) {
                          final List<({String filename, Uint8List bytes, String panelType})> fileItems = [];
                          for (final f in files) {
                            final bytes = await f.readAsBytes();
                            fileItems.add((filename: f.name, bytes: bytes, panelType: 'FRONT'));
                          }
                          _uploadFiles(fileItems);
                        }
                      },
                    ),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Color(0xFF334155)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      icon: const Icon(Icons.camera_alt, size: 16),
                      label: const Text('📷 Open Camera Scanner', style: TextStyle(fontSize: 11)),
                      onPressed: () => setState(() => _webcamOpen = true),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Uploaded Photos Grid
          if (images.isNotEmpty) ...[
            Text('Uploaded Package Evidence (${images.length})',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: images.asMap().entries.map((e) {
                final img = e.value as Map<String, dynamic>;
                final imgId = img['id'];
                final panelType = img['panel_type']?.toString() ?? 'FRONT';

                return Container(
                  width: 170,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        height: 120,
                        child: AuthorizedImage(
                          src: '/inspections/${_inspection!['id']}/images/$imgId/content',
                          alt: img['original_filename']?.toString(),
                          fit: BoxFit.contain,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        img['original_filename']?.toString() ?? 'photo.jpg',
                        style: const TextStyle(fontSize: 10, color: Color(0xFFCBD5E1), fontFamily: 'monospace'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<String>(
                        initialValue: panelType,
                        isDense: true,
                        decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 4)),
                        dropdownColor: const Color(0xFF131D31),
                        style: const TextStyle(fontSize: 10, color: Colors.white),
                        items: panels.map((p) => DropdownMenuItem(value: p, child: Text(p.replaceAll('_', ' ')))).toList(),
                        onChanged: (val) async {
                          if (val == null) return;
                          await ApiClient().patch('/inspections/${_inspection!['id']}/images/$imgId', body: {'panel_type': val});
                          _refreshInspection();
                        },
                      ),
                      const SizedBox(height: 6),
                      TextButton(
                        style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                        child: const Text('Remove Photo', style: TextStyle(fontSize: 10, color: AppTheme.rose)),
                        onPressed: () async {
                          await ApiClient().delete('/inspections/${_inspection!['id']}/images/$imgId');
                          _refreshInspection();
                        },
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 20),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () => _scan(_inspection!['id']),
                child: Text(_scanned ? 'Scan Again' : 'Scan Photos & Extract →',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStep2Review(List<dynamic> images) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('Mandatory LMPC Statutory Declarations & Review',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                  SizedBox(height: 2),
                  Text('Automated extraction for Legal Metrology (Packaged Commodities) Rules, 2011–2026.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                ],
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                ),
                icon: const Icon(Icons.refresh, size: 14),
                label: const Text('Scan Photos Again', style: TextStyle(fontSize: 11)),
                onPressed: () => _scan(_inspection!['id']),
              ),
            ],
          ),
          const SizedBox(height: 18),

          // Global Regulatory Status Banner
          Builder(
            builder: (context) {
              final prodMatch = _candidates.firstWhere(
                (c) => c['declaration_type']?.toString().toUpperCase() == 'COMMON_PRODUCT_NAME',
                orElse: () => null,
              );
              final prodName = prodMatch?['normalized_value']?.toString() ?? _inspection?['product_name']?.toString();
              if (prodName == null || prodName.isEmpty) return const SizedBox.shrink();

              final banInfo = (prodMatch?['structured_value'] as Map<String, dynamic>?)?['international_ban_info'] as Map<String, dynamic>? ??
                  (_inspection?['international_ban_info'] as Map<String, dynamic>?);
              final bStatus = banInfo?['status']?.toString() ?? 'PERMITTED';
              final isBanned = bStatus == 'BANNED' || banInfo?['is_banned'] == true;
              final isRestricted = bStatus == 'RESTRICTED';
              final bColor = isBanned ? AppTheme.rose : isRestricted ? AppTheme.amber : AppTheme.emerald;
              final bIcon = isBanned ? Icons.gavel_rounded : isRestricted ? Icons.warning_amber_rounded : Icons.verified_user_outlined;
              final bTitle = isBanned
                  ? 'GLOBAL REGULATORY WARNING: BANNED / PROHIBITED IN FOREIGN JURISDICTIONS'
                  : isRestricted
                      ? 'GLOBAL REGULATORY NOTICE: RESTRICTED / MANDATORY ALLERGEN RULES'
                      : 'GLOBAL REGULATORY STATUS: GLOBALLY PERMITTED';
              final bReason = banInfo?['reason']?.toString() ?? 'Standard packaged commodity. No overseas bans recorded.';
              final bCountries = ((banInfo?['countries'] ?? banInfo?['banned_countries']) as List?)?.map((e) => e.toString()).toList() ?? [];

              return Container(
                margin: const EdgeInsets.only(bottom: 18),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: bColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: bColor.withValues(alpha: 0.5), width: 1.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(bIcon, color: bColor, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '$bTitle — ${prodName.toUpperCase()}',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: bColor, letterSpacing: 0.5),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(bReason, style: const TextStyle(fontSize: 11, color: Colors.white, height: 1.4)),
                    if (bCountries.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: [
                          const Text('Prohibited In: ', style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                          ...bCountries.map((c) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                            decoration: BoxDecoration(
                              color: bColor.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: bColor.withValues(alpha: 0.5)),
                            ),
                            child: Text(c, style: TextStyle(fontSize: 9.5, color: bColor, fontWeight: FontWeight.bold)),
                          )),
                        ],
                      ),
                    ],
                  ],
                ),
              );
            },
          ),

          // Statutory Color & Dietary Label Marks
          Builder(
            builder: (context) {
              final colorMarks = (_analysisResult?['detected_color_marks'] as List?)
                      ?.map((e) => e as Map<String, dynamic>)
                      .toList() ??
                  [];
              if (colorMarks.isEmpty) return const SizedBox.shrink();

              return Container(
                margin: const EdgeInsets.only(bottom: 18),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.verified_outlined, color: AppTheme.emerald, size: 18),
                        const SizedBox(width: 8),
                        const Text(
                          'STATUTORY COLOR & DIETARY MARKS DETECTED',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                        ),
                        const Spacer(),
                        Text(
                          '${colorMarks.length} FOUND',
                          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 8,
                      children: colorMarks.map((m) {
                        final title = m['title']?.toString() ?? 'Mark';
                        final colorName = m['color_name']?.toString() ?? 'GREEN';
                        final conf = ((m['confidence'] as num?)?.toDouble() ?? 0.8) * 100;
                        Color cColor = colorName == 'GREEN'
                            ? AppTheme.emerald
                            : (colorName == 'RED_BROWN' ? AppTheme.rose : AppTheme.amber);

                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: cColor.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: cColor.withValues(alpha: 0.4)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 14,
                                height: 14,
                                decoration: BoxDecoration(
                                  color: cColor,
                                  shape: colorName == 'YELLOW_AMBER' ? BoxShape.rectangle : BoxShape.circle,
                                  borderRadius: colorName == 'YELLOW_AMBER' ? BorderRadius.circular(2) : null,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(title, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: cColor)),
                              const SizedBox(width: 6),
                              Text('${conf.toStringAsFixed(0)}%', style: TextStyle(fontSize: 9.5, color: cColor.withValues(alpha: 0.7))),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              );
            },
          ),

          // 12 Mandatory Declarations Status Grid
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'LMPC Rule 6 Mandatory Statutory Declarations Status (${_candidates.length} Detected)',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                ),
                const SizedBox(height: 12),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth >= 700;
                    final w = isWide ? (constraints.maxWidth - 24) / 3 : constraints.maxWidth;

                    return Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: mandatoryDeclarations.map((item) {
                        final matched = _candidates.where((c) {
                          final type = c['declaration_type']?.toString().toUpperCase() ?? '';
                          return type.contains(item.type) || item.type.contains(type);
                        }).toList();
                        final isFound = matched.isNotEmpty;
                        final mainMatch = isFound ? matched.first : null;

                        return Container(
                          width: w,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isFound ? const Color(0xFF131D31) : const Color(0xFF090D16),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isFound ? const Color(0x6610B981) : const Color(0xFF1E293B),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(item.label,
                                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: isFound ? const Color(0x3310B981) : const Color(0xFF1E293B),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      isFound ? '✓ Extracted' : '○ Not Detected',
                                      style: TextStyle(
                                        fontSize: 9,
                                        fontWeight: FontWeight.bold,
                                        color: isFound ? AppTheme.emerald : const Color(0xFF64748B),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              if (isFound && mainMatch != null) ...[
                                const SizedBox(height: 6),
                                Text(
                                  mainMatch['normalized_value']?.toString() ?? '',
                                  style: const TextStyle(fontSize: 11, color: AppTheme.emeraldLight, fontWeight: FontWeight.w500),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Confidence: ${((mainMatch['confidence_score'] as num? ?? 0) * 100).toStringAsFixed(0)}% · Panel: ${mainMatch['panel_type'] ?? 'PANEL'}',
                                  style: const TextStyle(fontSize: 9, color: Color(0xFF64748B), fontFamily: 'monospace'),
                                ),
                                if (item.type == 'COMMON_PRODUCT_NAME') ...[
                                  Builder(
                                    builder: (context) {
                                      final ban = (mainMatch['structured_value'] as Map<String, dynamic>?)?['international_ban_info'] as Map<String, dynamic>? ??
                                          (_inspection?['international_ban_info'] as Map<String, dynamic>?);
                                      final bStatus = ban?['status']?.toString() ?? 'PERMITTED';
                                      final isBanned = bStatus == 'BANNED' || ban?['is_banned'] == true;
                                      final isRestricted = bStatus == 'RESTRICTED';
                                      final bColor = isBanned ? AppTheme.rose : isRestricted ? AppTheme.amber : AppTheme.emerald;
                                      final bIcon = isBanned ? Icons.gavel_rounded : isRestricted ? Icons.warning_amber_rounded : Icons.verified_user_outlined;
                                      final bText = isBanned ? 'BANNED ABROAD' : isRestricted ? 'RESTRICTED ABROAD' : 'GLOBALLY PERMITTED';
                                      final bCountries = (ban?['countries'] as List?)?.join(', ') ?? '';

                                      return Container(
                                        margin: const EdgeInsets.only(top: 6),
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: bColor.withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(4),
                                          border: Border.all(color: bColor.withValues(alpha: 0.5)),
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(bIcon, size: 10, color: bColor),
                                            const SizedBox(width: 4),
                                            Flexible(
                                              child: Text(
                                                bCountries.isNotEmpty ? '$bText ($bCountries)' : bText,
                                                style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.bold, color: bColor),
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                                ],
                              ],
                            ],
                          ),
                        );
                      }).toList(),
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Bottom Step Actions
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                ),
                onPressed: () => setState(() => _step = 1),
                child: const Text('← Add or Retake Photos', style: TextStyle(fontSize: 11)),
              ),
              Row(
                children: [
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Color(0xFF334155)),
                    ),
                    onPressed: () => context.go('/inspections'),
                    child: const Text('Save Draft & Exit', style: TextStyle(fontSize: 11)),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.emerald,
                      foregroundColor: const Color(0xFF090D16),
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: images.isNotEmpty ? _submitAndAnalyze : null,
                    child: const Text('Submit & Run Full Automated Analysis →',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
