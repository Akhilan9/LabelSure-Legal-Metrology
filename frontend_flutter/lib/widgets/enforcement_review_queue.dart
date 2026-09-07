import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class EnforcementReviewQueueWidget extends StatefulWidget {
  const EnforcementReviewQueueWidget({super.key});

  @override
  State<EnforcementReviewQueueWidget> createState() => _EnforcementReviewQueueWidgetState();
}

class _EnforcementReviewQueueWidgetState extends State<EnforcementReviewQueueWidget> {
  Map<String, dynamic>? _queueData;
  bool _loading = true;
  String _statusFilter = 'ALL';
  String _urgencyFilter = 'ALL';
  String _categoryFilter = '';

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() => _loading = true);
    try {
      final params = <String, String>{};
      if (_statusFilter != 'ALL') params['status'] = _statusFilter;
      if (_urgencyFilter != 'ALL') params['urgency'] = _urgencyFilter;
      if (_categoryFilter.isNotEmpty) params['category'] = _categoryFilter;

      final data = await ApiClient().get('/dashboard/review-queue', queryParams: params);
      if (mounted) {
        setState(() {
          _queueData = data is Map<String, dynamic> ? data : null;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _queueData = null;
          _loading = false;
        });
      }
    }
  }

  Color _getUrgencyColor(String urgency) {
    switch (urgency.toUpperCase()) {
      case 'CRITICAL':
        return AppTheme.rose;
      case 'HIGH':
        return const Color(0xFFF97316);
      case 'MEDIUM':
        return AppTheme.amber;
      case 'LOW':
      default:
        return AppTheme.emerald;
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = (_queueData?['items'] as List?) ?? [];
    final total = _queueData?['total'] ?? 0;
    final criticalCount = _queueData?['critical_count'] ?? 0;
    final highCount = _queueData?['high_count'] ?? 0;
    final mediumCount = _queueData?['medium_count'] ?? 0;

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header with Urgency Badges
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'PRIORITIZED INSPECTOR REVIEW QUEUE',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF1E293B),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            '$total Records',
                            style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFFCBD5E1)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Algorithmic urgency scoring prioritized by non-compliant rules, low-confidence OCR, overrides, and SLA age.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),

              // Urgency Filter Buttons
              Wrap(
                spacing: 6,
                children: [
                  _buildUrgencyChip('CRITICAL', '🔥 $criticalCount Critical', AppTheme.rose),
                  _buildUrgencyChip('HIGH', '⚠️ $highCount High', const Color(0xFFF97316)),
                  _buildUrgencyChip('MEDIUM', '🟡 $mediumCount Medium', AppTheme.amber),
                  _buildUrgencyChip('ALL', 'All Tiers', Colors.white),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Filters Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF131D31),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                const Text('STATUS: ', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
                const SizedBox(width: 6),
                ...['ALL', 'NEEDS_REVIEW', 'UNDER_REVIEW', 'FINALIZED'].map((st) {
                  final active = _statusFilter == st;
                  return Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: InkWell(
                      onTap: () {
                        setState(() => _statusFilter = st);
                        _fetch();
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: active ? const Color(0x3310B981) : Colors.transparent,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: active ? AppTheme.emerald : Colors.transparent,
                          ),
                        ),
                        child: Text(
                          st.replaceAll('_', ' '),
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: active ? FontWeight.bold : FontWeight.normal,
                            color: active ? AppTheme.emerald : const Color(0xFF94A3B8),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
                const Spacer(),
                DropdownButton<String>(
                  value: _categoryFilter,
                  dropdownColor: const Color(0xFF131D31),
                  underline: const SizedBox.shrink(),
                  style: const TextStyle(fontSize: 11, color: Colors.white),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('All Categories')),
                    DropdownMenuItem(value: 'FOOD', child: Text('Packaged Food')),
                    DropdownMenuItem(value: 'BEVERAGES', child: Text('Beverages')),
                    DropdownMenuItem(value: 'COSMETICS', child: Text('Cosmetics')),
                    DropdownMenuItem(value: 'ELECTRONICS', child: Text('Electronics')),
                    DropdownMenuItem(value: 'PHARMACEUTICALS', child: Text('Pharmaceuticals')),
                    DropdownMenuItem(value: 'GENERAL', child: Text('General')),
                  ],
                  onChanged: (val) {
                    setState(() => _categoryFilter = val ?? '');
                    _fetch();
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Items Table
          if (_loading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
            )
          else if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Text('No inspection cases in current review filter.', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowHeight: 36,
                dataRowMinHeight: 44,
                dataRowMaxHeight: 52,
                horizontalMargin: 12,
                columnSpacing: 24,
                headingTextStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 0.5),
                columns: const [
                  DataColumn(label: Text('CODE')),
                  DataColumn(label: Text('COMMODITY / BRAND')),
                  DataColumn(label: Text('URGENCY')),
                  DataColumn(label: Text('STATUS')),
                  DataColumn(label: Text('VIOLATIONS')),
                  DataColumn(label: Text('ACTION')),
                ],
                rows: items.map((item) {
                  final urgency = item['urgency_tier']?.toString() ?? 'MEDIUM';
                  final urgencyColor = _getUrgencyColor(urgency);
                  final inspId = item['id']?.toString() ?? '';

                  return DataRow(
                    cells: [
                      DataCell(Text(
                        item['inspection_code']?.toString() ?? '',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: AppTheme.emerald),
                      )),
                      DataCell(Text(
                        item['product_name']?.toString() ?? 'Packaged Commodity',
                        style: const TextStyle(fontSize: 11, color: Colors.white),
                      )),
                      DataCell(Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: urgencyColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: urgencyColor.withValues(alpha: 0.4)),
                        ),
                        child: Text(urgency, style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: urgencyColor)),
                      )),
                      DataCell(Text(
                        item['status']?.toString() ?? '',
                        style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
                      )),
                      DataCell(Text(
                        '${item['violation_count'] ?? 0} non-compliant',
                        style: const TextStyle(fontSize: 10, color: AppTheme.rose),
                      )),
                      DataCell(
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0x2610B981),
                            foregroundColor: AppTheme.emerald,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(6),
                              side: const BorderSide(color: Color(0x4D10B981)),
                            ),
                          ),
                          onPressed: () => context.go('/inspections/$inspId'),
                          child: const Text('Review Case →', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildUrgencyChip(String urgency, String label, Color color) {
    final active = _urgencyFilter == urgency;
    return InkWell(
      onTap: () {
        setState(() => _urgencyFilter = urgency);
        _fetch();
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: active ? color.withValues(alpha: 0.25) : const Color(0xFF131D31),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: active ? color : const Color(0xFF334155),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: active ? FontWeight.bold : FontWeight.normal,
            color: active ? color : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }
}
