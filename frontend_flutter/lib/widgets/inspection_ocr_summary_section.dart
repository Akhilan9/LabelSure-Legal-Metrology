import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme.dart';

class InspectionOCRSummarySection extends StatefulWidget {
  final Map<String, dynamic>? summary;
  final bool loading;
  final VoidCallback onTriggerBatchOCR;
  final ValueChanged<String>? onOpenImageModal;
  final bool canEdit;

  const InspectionOCRSummarySection({
    super.key,
    required this.summary,
    this.loading = false,
    required this.onTriggerBatchOCR,
    this.onOpenImageModal,
    this.canEdit = false,
  });

  @override
  State<InspectionOCRSummarySection> createState() => _InspectionOCRSummarySectionState();
}

class _InspectionOCRSummarySectionState extends State<InspectionOCRSummarySection> {
  int _activePanelIdx = 0;
  bool _copied = false;

  @override
  Widget build(BuildContext context) {
    if (widget.loading) {
      return Container(
        decoration: AppTheme.glassPanel(),
        padding: const EdgeInsets.all(24),
        child: const Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
      );
    }

    final panels = (widget.summary?['panels'] as List?) ?? [];
    if (panels.isEmpty) {
      return Container(
        decoration: AppTheme.glassPanel(),
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Text('OCR EXTRACTED EVIDENCE TEXT',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
            const SizedBox(height: 8),
            const Text('No OCR text recognition run yet for these package photos.',
                style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
            if (widget.canEdit) ...[
              const SizedBox(height: 12),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.document_scanner, size: 16),
                label: const Text('Run OCR on All Panels', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                onPressed: widget.onTriggerBatchOCR,
              ),
            ],
          ],
        ),
      );
    }

    final currentPanel = _activePanelIdx < panels.length ? panels[_activePanelIdx] as Map<String, dynamic> : panels.first as Map<String, dynamic>;
    final textLines = (currentPanel['text_lines'] as List?)?.map((e) => e.toString()).toList() ?? [];

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Section Title & Action
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'EXTRACTED PACKAGE EVIDENCE TEXT (OCR OBSERVATION)',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Deterministic and deep learning text recognition across all package panels.',
                    style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                  ),
                ],
              ),
              const Spacer(),
              if (widget.canEdit)
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.emerald,
                    side: const BorderSide(color: Color(0x4D10B981)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  ),
                  icon: const Icon(Icons.refresh, size: 14),
                  label: const Text('Re-run OCR', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                  onPressed: widget.onTriggerBatchOCR,
                ),
            ],
          ),
          const SizedBox(height: 14),

          // Panels Tabs
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: panels.asMap().entries.map((entry) {
                final idx = entry.key;
                final p = entry.value as Map<String, dynamic>;
                final active = _activePanelIdx == idx;
                final panelType = p['panel_type']?.toString() ?? 'PANEL';
                final linesCount = (p['text_lines'] as List?)?.length ?? 0;

                return Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: InkWell(
                    onTap: () => setState(() => _activePanelIdx = idx),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: active ? const Color(0x2610B981) : const Color(0xFF131D31),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: active ? AppTheme.emerald : const Color(0xFF1E293B),
                        ),
                      ),
                      child: Text(
                        '$panelType ($linesCount)',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: active ? FontWeight.bold : FontWeight.normal,
                          color: active ? AppTheme.emerald : const Color(0xFF94A3B8),
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 12),

          // Active Panel Text Container
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF0D1527),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Text(
                      'Panel Side: ${currentPanel['panel_type']}',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    const Spacer(),
                    TextButton.icon(
                      style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                      icon: Icon(_copied ? Icons.check : Icons.copy, size: 13, color: AppTheme.emerald),
                      label: Text(
                        _copied ? 'Copied' : 'Copy Panel Text',
                        style: const TextStyle(fontSize: 10, color: AppTheme.emerald),
                      ),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: textLines.join('\n')));
                        setState(() => _copied = true);
                        Future.delayed(const Duration(seconds: 2), () {
                          if (mounted) setState(() => _copied = false);
                        });
                      },
                    ),
                  ],
                ),
                const Divider(color: Color(0xFF1E293B), height: 16),
                if (textLines.isEmpty)
                  const Text('No text recognized on this panel.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B)))
                else
                  SelectableText(
                    textLines.join('\n'),
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.6,
                      color: Color(0xFFCBD5E1),
                      fontFamily: 'monospace',
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
