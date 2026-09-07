import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme.dart';
import 'ocr_bounding_box_canvas.dart';

class OCRBlockTable extends StatefulWidget {
  final List<OCRBlockData> blocks;
  final String? selectedBlockId;
  final String? hoveredBlockId;
  final ValueChanged<OCRBlockData>? onSelectBlock;
  final ValueChanged<String?>? onHoverBlock;

  const OCRBlockTable({
    super.key,
    required this.blocks,
    this.selectedBlockId,
    this.hoveredBlockId,
    this.onSelectBlock,
    this.onHoverBlock,
  });

  @override
  State<OCRBlockTable> createState() => _OCRBlockTableState();
}

class _OCRBlockTableState extends State<OCRBlockTable> {
  String _search = '';
  String _tierFilter = 'ALL';
  String? _copiedId;

  @override
  Widget build(BuildContext context) {
    final filtered = widget.blocks.where((b) {
      if (_tierFilter != 'ALL' && b.confidenceTier != _tierFilter) return false;
      if (_search.trim().isNotEmpty) {
        final query = _search.toLowerCase();
        return b.rawText.toLowerCase().contains(query) ||
            b.normalizedText.toLowerCase().contains(query);
      }
      return true;
    }).toList();

    return Container(
      decoration: AppTheme.glassPanel(
        color: const Color(0xFF131D31),
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header & Search
          Row(
            children: [
              Text(
                'Extracted Text Blocks (${widget.blocks.length})',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
              ),
              const Spacer(),
              if (_copiedId != null)
                const Text(
                  'Copied to clipboard!',
                  style: TextStyle(fontSize: 11, color: AppTheme.emerald, fontWeight: FontWeight.w600),
                ),
            ],
          ),
          const SizedBox(height: 8),

          // Search Field
          TextField(
            onChanged: (val) => setState(() => _search = val),
            style: const TextStyle(fontSize: 12, color: Colors.white),
            decoration: InputDecoration(
              isDense: true,
              hintText: 'Search text blocks…',
              prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
              fillColor: const Color(0xFF0A0F1D),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 8),

          // Tier Filter Pills
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildTierChip('ALL', 'All (${widget.blocks.length})', null),
                const SizedBox(width: 4),
                _buildTierChip(
                  'GOOD',
                  'Good (${widget.blocks.where((b) => b.confidenceTier == 'GOOD').length})',
                  AppTheme.goodTier,
                ),
                const SizedBox(width: 4),
                _buildTierChip(
                  'REVIEW',
                  'Review (${widget.blocks.where((b) => b.confidenceTier == 'REVIEW').length})',
                  AppTheme.reviewTier,
                ),
                const SizedBox(width: 4),
                _buildTierChip(
                  'LOW',
                  'Low (${widget.blocks.where((b) => b.confidenceTier == 'LOW').length})',
                  AppTheme.lowTier,
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          const Divider(color: Color(0xFF1E293B), height: 1),

          // Blocks List
          Expanded(
            child: filtered.isEmpty
                ? const Center(
                    child: Text('No blocks matched filter.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                  )
                : ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (_, _) => const Divider(color: Color(0xFF1E293B), height: 1),
                    itemBuilder: (context, index) {
                      final block = filtered[index];
                      final isSelected = widget.selectedBlockId == block.id;

                      Color badgeColor;
                      switch (block.confidenceTier) {
                        case 'GOOD':
                          badgeColor = AppTheme.goodTier;
                          break;
                        case 'LOW':
                          badgeColor = AppTheme.lowTier;
                          break;
                        case 'REVIEW':
                        default:
                          badgeColor = AppTheme.reviewTier;
                          break;
                      }

                      return InkWell(
                        onTap: () => widget.onSelectBlock?.call(block),
                        onHover: (hover) => widget.onHoverBlock?.call(hover ? block.id : null),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                          decoration: BoxDecoration(
                            color: isSelected ? const Color(0x3310B981) : Colors.transparent,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isSelected ? AppTheme.emerald : Colors.transparent,
                              width: 1,
                            ),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Order number badge
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                decoration: BoxDecoration(
                                  color: badgeColor.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: badgeColor.withValues(alpha: 0.5)),
                                ),
                                child: Text(
                                  '#${block.readingOrder + 1}',
                                  style: TextStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.bold,
                                    fontFamily: 'monospace',
                                    color: badgeColor,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),

                              // Text content
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      block.rawText,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w500,
                                        color: Colors.white,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Row(
                                      children: [
                                        Text(
                                          'Conf: ${(block.confidence * 100).toStringAsFixed(0)}%',
                                          style: TextStyle(fontSize: 9, color: badgeColor, fontFamily: 'monospace'),
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          'Line ${block.lineNumber + 1}',
                                          style: const TextStyle(fontSize: 9, color: Color(0xFF64748B)),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),

                              // Copy button
                              IconButton(
                                icon: const Icon(Icons.copy, size: 13, color: Color(0xFF94A3B8)),
                                padding: EdgeInsets.zero,
                                constraints: const BoxConstraints(),
                                tooltip: 'Copy text',
                                onPressed: () {
                                  Clipboard.setData(ClipboardData(text: block.rawText));
                                  setState(() => _copiedId = block.id);
                                  Future.delayed(const Duration(seconds: 2), () {
                                    if (mounted) setState(() => _copiedId = null);
                                  });
                                },
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildTierChip(String tier, String label, Color? color) {
    final active = _tierFilter == tier;
    return InkWell(
      onTap: () => setState(() => _tierFilter = tier),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: active ? (color ?? Colors.white).withValues(alpha: 0.2) : const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: active ? (color ?? Colors.white) : const Color(0xFF334155),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: active ? FontWeight.bold : FontWeight.normal,
            color: active ? Colors.white : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }
}
