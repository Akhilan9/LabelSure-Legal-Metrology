import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/theme.dart';
import 'ocr_bounding_box_canvas.dart';

class ExtractedDeclarationsSection extends StatefulWidget {
  final Map<String, dynamic> inspection;
  final VoidCallback? onExtractionComplete;

  const ExtractedDeclarationsSection({
    super.key,
    required this.inspection,
    this.onExtractionComplete,
  });

  @override
  State<ExtractedDeclarationsSection> createState() => _ExtractedDeclarationsSectionState();
}

class _ExtractedDeclarationsSectionState extends State<ExtractedDeclarationsSection> {
  List<dynamic> _candidates = [];
  Map<String, dynamic>? _summary;
  bool _loading = false;
  bool _extracting = false;
  Map<String, dynamic>? _selectedCandidate;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final id = widget.inspection['id'];
      final cRes = await ApiClient().get('/inspections/$id/declarations?limit=1000');
      final sRes = await ApiClient().get('/inspections/$id/extraction-summary');
      if (mounted) {
        setState(() {
          _candidates = cRes is List ? cRes : [];
          _summary = sRes is Map<String, dynamic> ? sRes : null;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _extract() async {
    setState(() => _extracting = true);
    try {
      final id = widget.inspection['id'];
      await ApiClient().post('/inspections/$id/extract-declarations');
      await _load();
      widget.onExtractionComplete?.call();
    } catch (_) {
      // Failed
    } finally {
      if (mounted) setState(() => _extracting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header & Action
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'EXTRACTED DECLARATIONS',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                        ),
                        const SizedBox(width: 8),
                        if (_summary != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF1E293B),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '${_candidates.length} Detected',
                              style: const TextStyle(fontSize: 10, color: Color(0xFFCBD5E1), fontFamily: 'monospace'),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Machine-generated statutory candidates for inspector review. Does not establish final legal compliance.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                icon: _extracting
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.bolt, size: 16),
                label: Text(
                  _extracting ? 'Extracting…' : 'Extract Declarations',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                ),
                onPressed: _extracting ? null : _extract,
              ),
            ],
          ),
          const SizedBox(height: 16),

          if (_loading)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
            )
          else if (_candidates.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF131D31),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text(
                  'No declarations extracted yet. Run OCR, then click "Extract Declarations".',
                  style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                ),
              ),
            )
          else ...[
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowHeight: 38,
                dataRowMinHeight: 48,
                dataRowMaxHeight: 56,
                columnSpacing: 20,
                headingTextStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B)),
                columns: const [
                  DataColumn(label: Text('DECLARATION')),
                  DataColumn(label: Text('NORMALIZED VALUE')),
                  DataColumn(label: Text('CONFIDENCE')),
                  DataColumn(label: Text('PANEL')),
                  DataColumn(label: Text('METHOD')),
                  DataColumn(label: Text('REVIEW')),
                  DataColumn(label: Text('EVIDENCE')),
                ],
                rows: _candidates.map((c) {
                  final type = c['declaration_type']?.toString().replaceAll('_', ' ') ?? '';
                  final val = c['normalized_value']?.toString() ?? '';
                  final conf = ((c['confidence_score'] as num? ?? 0) * 100).toStringAsFixed(0);
                  final panel = c['panel_type']?.toString() ?? 'FRONT';
                  final method = c['extraction_method']?.toString().replaceAll('_', ' ') ?? '';
                  final needsReview = c['needs_review'] == true;

                  return DataRow(
                    cells: [
                      DataCell(Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(type, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                          if (c['is_primary'] == true)
                            const Text('Primary candidate', style: TextStyle(fontSize: 9, color: AppTheme.emerald)),
                        ],
                      )),
                      DataCell(ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 240),
                        child: Text(val, style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1)), maxLines: 2, overflow: TextOverflow.ellipsis),
                      )),
                      DataCell(Text('$conf%', style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.white))),
                      DataCell(Text(panel, style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)))),
                      DataCell(Text(method, style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)))),
                      DataCell(Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: needsReview ? const Color(0x33F59E0B) : const Color(0x3310B981),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          needsReview ? 'Review Required' : 'Auto Extracted',
                          style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: needsReview ? AppTheme.amber : AppTheme.emerald),
                        ),
                      )),
                      DataCell(
                        TextButton(
                          style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
                          child: const Text('View Evidence', style: TextStyle(fontSize: 10, color: AppTheme.emerald, decoration: TextDecoration.underline)),
                          onPressed: () => setState(() => _selectedCandidate = c),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),

            // Evidence Viewer Card when selected
            if (_selectedCandidate != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Source Evidence · ${_selectedCandidate!['declaration_type']?.toString().replaceAll('_', ' ')}',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 18, color: Colors.white),
                          onPressed: () => setState(() => _selectedCandidate = null),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Value: "${_selectedCandidate!['normalized_value']}"',
                      style: const TextStyle(fontSize: 12, color: AppTheme.emerald, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Source Image ID: ${_selectedCandidate!['source_image_id']} · OCR Run: ${_selectedCandidate!['source_ocr_run_id'] ?? 'latest'}',
                      style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFF64748B)),
                    ),
                    const SizedBox(height: 12),

                    // OCR canvas for source photo
                    SizedBox(
                      height: 320,
                      child: OCRBoundingBoxCanvas(
                        imageUrl: '/inspections/${widget.inspection['id']}/images/${_selectedCandidate!['source_image_id']}/content',
                        blocks: ((_selectedCandidate!['sources'] as List?) ?? []).asMap().entries.map((e) {
                          return OCRBlockData.fromJson(e.value as Map<String, dynamic>, e.key);
                        }).toList(),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
