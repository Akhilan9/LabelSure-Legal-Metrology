import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:universal_html/html.dart' as html;
import '../core/api_client.dart';
import '../core/theme.dart';

class ReportsPage extends StatefulWidget {
  const ReportsPage({super.key});

  @override
  State<ReportsPage> createState() => _ReportsPageState();
}

class _ReportsPageState extends State<ReportsPage> {
  List<dynamic> _items = [];
  int _total = 0;
  int _page = 1;
  final TextEditingController _searchCtrl = TextEditingController();
  bool _loading = false;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() => _loading = true);
    try {
      final query = _searchCtrl.text.trim();
      final res = await ApiClient().get('/inspections', queryParams: {
        'page': _page,
        'page_size': 20,
        if (query.isNotEmpty) 'q': query,
      });

      if (mounted && res is Map<String, dynamic>) {
        setState(() {
          _items = (res['items'] as List?) ?? [];
          _total = res['total'] as int? ?? 0;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _download(String id, String code, String format) async {
    setState(() => _busyId = '$id-$format');
    try {
      final bytes = await ApiClient().getBytes('/inspections/$id/reports/$format');
      if (kIsWeb) {
        final blob = html.Blob([bytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        html.AnchorElement(href: url)
          ..setAttribute('download', '$code.$format')
          ..click();
        html.Url.revokeObjectUrl(url);
      }
    } catch (_) {}
    if (mounted) setState(() => _busyId = null);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('CASE EXPORTS & STATUTORY ARCHIVE',
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 1)),
        const SizedBox(height: 4),
        const Text('Compliance Reports',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 2),
        const Text('Download official packaged commodity inspection findings and evidence records.',
            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
        const SizedBox(height: 18),

        // Search
        Container(
          padding: const EdgeInsets.all(14),
          decoration: AppTheme.glassPanel(),
          child: TextField(
            controller: _searchCtrl,
            onSubmitted: (_) {
              setState(() => _page = 1);
              _fetch();
            },
            style: const TextStyle(fontSize: 12, color: Colors.white),
            decoration: InputDecoration(
              isDense: true,
              hintText: 'Find a case by case number, product or manufacturer…',
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
        const SizedBox(height: 16),

        // Cases List
        if (_loading)
          const Padding(
            padding: EdgeInsets.all(48),
            child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
          )
        else if (_items.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            decoration: AppTheme.glassPanel(),
            child: const Center(
              child: Text('No matching cases found.', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
            ),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = _items[index] as Map<String, dynamic>;
              final id = item['id']?.toString() ?? '';
              final code = item['inspection_code']?.toString() ?? 'case';

              return Container(
                padding: const EdgeInsets.all(16),
                decoration: AppTheme.glassPanel(),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          InkWell(
                            onTap: () => context.go('/inspections/$id'),
                            child: Text(
                              code,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                fontFamily: 'monospace',
                                color: AppTheme.emerald,
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${item['product_name'] ?? 'Untitled package'} · ${item['images_count'] ?? 0} photos',
                            style: const TextStyle(fontSize: 11, color: Colors.white),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            item['status']?.toString() ?? '',
                            style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                          ),
                        ],
                      ),
                    ),
                    Wrap(
                      spacing: 8,
                      children: ['pdf', 'csv', 'json'].map((format) {
                        final isBusy = _busyId == '$id-$format';

                        return OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white,
                            side: const BorderSide(color: Color(0xFF334155)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                          icon: isBusy
                              ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.emerald))
                              : const Icon(Icons.file_download, size: 14, color: AppTheme.emerald),
                          label: Text(format.toUpperCase(), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                          onPressed: isBusy ? null : () => _download(id, code, format),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              );
            },
          ),
        const SizedBox(height: 16),

        // Pagination
        Container(
          padding: const EdgeInsets.all(14),
          decoration: AppTheme.glassPanel(),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              OutlinedButton(
                onPressed: _page <= 1
                    ? null
                    : () {
                        setState(() => _page--);
                        _fetch();
                      },
                child: const Text('Previous', style: TextStyle(fontSize: 11)),
              ),
              Text('Page $_page · $_total cases', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
              OutlinedButton(
                onPressed: _page * 20 >= _total
                    ? null
                    : () {
                        setState(() => _page++);
                        _fetch();
                      },
                child: const Text('Next', style: TextStyle(fontSize: 11)),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
