import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class InspectionsListPage extends StatefulWidget {
  const InspectionsListPage({super.key});

  @override
  State<InspectionsListPage> createState() => _InspectionsListPageState();
}

class _InspectionsListPageState extends State<InspectionsListPage> {
  List<dynamic> _inspections = [];
  int _total = 0;
  int _page = 1;
  final int _pageSize = 15;
  String _statusFilter = '';
  final TextEditingController _searchCtrl = TextEditingController();
  bool _loading = true;
  final Set<String> _selectedIds = {};
  bool _bulkProcessing = false;

  final statusOptions = [
    ('', 'All Statuses'),
    ('DRAFT', 'Draft'),
    ('EVIDENCE_UPLOADED', 'Evidence Uploaded'),
    ('READY_FOR_ANALYSIS', 'Ready for Analysis'),
  ];

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() => _loading = true);
    try {
      final params = <String, dynamic>{
        'page': _page,
        'page_size': _pageSize,
      };
      if (_statusFilter.isNotEmpty) params['status'] = _statusFilter;
      if (_searchCtrl.text.trim().isNotEmpty) params['q'] = _searchCtrl.text.trim();

      final res = await ApiClient().get('/inspections', queryParams: params);
      if (mounted && res is Map<String, dynamic>) {
        setState(() {
          _inspections = (res['items'] as List?) ?? [];
          _total = res['total'] as int? ?? 0;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _bulkScan() async {
    if (_selectedIds.isEmpty) return;
    setState(() => _bulkProcessing = true);
    try {
      final res = await ApiClient().post('/inspections/bulk-analysis', body: {
        'inspection_ids': _selectedIds.toList(),
      });
      final total = res is Map ? (res['total'] ?? _selectedIds.length) : _selectedIds.length;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bulk scanning completed! Processed $total inspections.')),
        );
        setState(() => _selectedIds.clear());
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bulk scanning error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _bulkProcessing = false);
    }
  }

  Widget _buildStatusBadge(String status) {
    Color bg;
    Color text;

    switch (status) {
      case 'DRAFT':
        bg = const Color(0xFF1E293B);
        text = const Color(0xFF94A3B8);
        break;
      case 'EVIDENCE_UPLOADED':
        bg = const Color(0x3306B6D4);
        text = AppTheme.cyan;
        break;
      case 'READY_FOR_ANALYSIS':
        bg = const Color(0x33F59E0B);
        text = AppTheme.amber;
        break;
      case 'COMPLIANT':
        bg = const Color(0x3310B981);
        text = AppTheme.emerald;
        break;
      case 'NON_COMPLIANT':
        bg = const Color(0x33F43F5E);
        text = AppTheme.rose;
        break;
      default:
        bg = const Color(0xFF1E293B);
        text = Colors.white;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        status.replaceAll('_', ' '),
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: text),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text('REGULATORY LOG & REPOSITORY',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 1)),
                SizedBox(height: 4),
                Text('Inspection Repository',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
                SizedBox(height: 2),
                Text('Browse, search, and verify packaged commodity inspections and submitted evidence.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
              ],
            ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.emerald,
                foregroundColor: const Color(0xFF090D16),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('New Inspection', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              onPressed: () => context.go('/inspections/new'),
            ),
          ],
        ),
        const SizedBox(height: 18),

        // Bulk Action Bar
        if (_selectedIds.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF064E3B),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.emerald),
            ),
            child: Row(
              children: [
                Text(
                  '⚡ Bulk Action: ${_selectedIds.length} inspection${_selectedIds.length > 1 ? 's' : ''} selected',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const Spacer(),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.emerald,
                    foregroundColor: const Color(0xFF090D16),
                  ),
                  onPressed: _bulkProcessing ? null : _bulkScan,
                  child: Text(_bulkProcessing ? 'Scanning…' : '⚡ Bulk Scan Selected Packages',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () => setState(() => _selectedIds.clear()),
                  child: const Text('Clear Selection', style: TextStyle(fontSize: 11, color: Colors.white)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],

        // Search & Filters Bar
        Container(
          padding: const EdgeInsets.all(14),
          decoration: AppTheme.glassPanel(),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchCtrl,
                  onSubmitted: (_) {
                    setState(() => _page = 1);
                    _fetch();
                  },
                  style: const TextStyle(fontSize: 12, color: Colors.white),
                  decoration: InputDecoration(
                    isDense: true,
                    hintText: 'Search code, product, brand, barcode…',
                    prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.arrow_forward, size: 16, color: AppTheme.emerald),
                      onPressed: () {
                        setState(() => _page = 1);
                        _fetch();
                      },
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: statusOptions.map((opt) {
                    final active = _statusFilter == opt.$1;
                    return Padding(
                      padding: const EdgeInsets.only(left: 6),
                      child: InkWell(
                        onTap: () {
                          setState(() {
                            _statusFilter = opt.$1;
                            _page = 1;
                          });
                          _fetch();
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                          decoration: BoxDecoration(
                            color: active ? const Color(0x3310B981) : const Color(0xFF131D31),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: active ? AppTheme.emerald : const Color(0xFF1E293B),
                            ),
                          ),
                          child: Text(
                            opt.$2,
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
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Table
        Container(
          decoration: AppTheme.glassPanel(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(48),
                  child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
                )
              else if (_inspections.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(48),
                  child: Center(
                    child: Text('No inspections found. Create your first inspection to start.',
                        style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                  ),
                )
              else
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    headingRowHeight: 40,
                    dataRowMinHeight: 50,
                    dataRowMaxHeight: 58,
                    columns: [
                      DataColumn(
                        label: Checkbox(
                          value: _inspections.isNotEmpty && _selectedIds.length == _inspections.length,
                          activeColor: AppTheme.emerald,
                          onChanged: (val) {
                            setState(() {
                              if (val == true) {
                                _selectedIds.addAll(_inspections.map((i) => i['id']?.toString() ?? ''));
                              } else {
                                _selectedIds.clear();
                              }
                            });
                          },
                        ),
                      ),
                      const DataColumn(label: Text('CODE')),
                      const DataColumn(label: Text('PRODUCT & BRAND')),
                      const DataColumn(label: Text('CATEGORY')),
                      const DataColumn(label: Text('STATUS')),
                      const DataColumn(label: Text('EVIDENCE')),
                      const DataColumn(label: Text('CREATED BY')),
                      const DataColumn(label: Text('DATE')),
                      const DataColumn(label: Text('ACTION')),
                    ],
                    rows: _inspections.map((insp) {
                      final id = insp['id']?.toString() ?? '';
                      final isSelected = _selectedIds.contains(id);
                      final dateStr = insp['created_at'] != null
                          ? DateFormat.yMMMd().format(DateTime.tryParse(insp['created_at']) ?? DateTime.now())
                          : '—';

                      return DataRow(
                        selected: isSelected,
                        onSelectChanged: (_) {
                          context.go('/inspections/$id');
                        },
                        cells: [
                          DataCell(
                            Checkbox(
                              value: isSelected,
                              activeColor: AppTheme.emerald,
                              onChanged: (v) {
                                setState(() {
                                  if (v == true) {
                                    _selectedIds.add(id);
                                  } else {
                                    _selectedIds.remove(id);
                                  }
                                });
                              },
                            ),
                          ),
                          DataCell(Text(
                            insp['inspection_code']?.toString() ?? '',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: AppTheme.emerald),
                          )),
                          DataCell(Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(insp['product_name']?.toString() ?? '—', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                              if (insp['international_ban_info'] != null &&
                                  (insp['international_ban_info']['is_banned'] == true ||
                                      insp['international_ban_info']['status'] == 'RESTRICTED')) ...[
                                const SizedBox(height: 2),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                  decoration: BoxDecoration(
                                    color: (insp['international_ban_info']['is_banned'] == true ? AppTheme.rose : AppTheme.amber).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(3),
                                    border: Border.all(
                                      color: (insp['international_ban_info']['is_banned'] == true ? AppTheme.rose : AppTheme.amber).withValues(alpha: 0.5),
                                    ),
                                  ),
                                  child: Text(
                                    insp['international_ban_info']['is_banned'] == true ? '✕ Banned Abroad' : '⚠ Restricted Abroad',
                                    style: TextStyle(
                                      fontSize: 8.5,
                                      fontWeight: FontWeight.bold,
                                      color: insp['international_ban_info']['is_banned'] == true ? AppTheme.rose : AppTheme.amber,
                                    ),
                                  ),
                                ),
                              ] else ...[
                                Text(insp['brand_name']?.toString() ?? 'No brand specified', style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
                              ],
                            ],
                          )),
                          DataCell(Text(insp['category']?.toString() ?? '—', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)))),
                          DataCell(_buildStatusBadge(insp['status']?.toString() ?? '')),
                          DataCell(Text('${insp['images_count'] ?? 0} images', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)))),
                          DataCell(Text(insp['created_by_name']?.toString() ?? 'Inspector', style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1)))),
                          DataCell(Text(dateStr, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)))),
                          DataCell(
                            TextButton(
                              style: TextButton.styleFrom(foregroundColor: AppTheme.emerald),
                              onPressed: () => context.go('/inspections/$id'),
                              child: const Text('Details →', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ],
                      );
                    }).toList(),
                  ),
                ),

              // Pagination
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: Color(0xFF1E293B))),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Showing ${_inspections.length} of $_total inspections',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                    Row(
                      children: [
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFF334155)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          ),
                          onPressed: _page <= 1
                              ? null
                              : () {
                                  setState(() => _page--);
                                  _fetch();
                                },
                          child: const Text('Previous', style: TextStyle(fontSize: 11)),
                        ),
                        const SizedBox(width: 8),
                        Text('Page $_page', style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.white)),
                        const SizedBox(width: 8),
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFF334155)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          ),
                          onPressed: (_page * _pageSize >= _total)
                              ? null
                              : () {
                                  setState(() => _page++);
                                  _fetch();
                                },
                          child: const Text('Next', style: TextStyle(fontSize: 11)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
