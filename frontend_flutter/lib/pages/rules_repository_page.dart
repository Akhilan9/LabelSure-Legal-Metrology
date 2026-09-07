import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class RulesRepositoryPage extends StatefulWidget {
  const RulesRepositoryPage({super.key});

  @override
  State<RulesRepositoryPage> createState() => _RulesRepositoryPageState();
}

class _RulesRepositoryPageState extends State<RulesRepositoryPage> {
  List<dynamic> _items = [];
  String _selected = '';
  final TextEditingController _queryCtrl = TextEditingController();
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    try {
      final res = await ApiClient().get('/rules');
      if (mounted && res is Map<String, dynamic>) {
        setState(() {
          _items = (res['items'] as List?) ?? [];
          _selected = res['configured']?.toString() ?? (_items.isNotEmpty ? _items.first['ruleset_id'] : '');
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentRuleset = _items.firstWhere(
      (item) => item['ruleset_id'] == _selected,
      orElse: () => null,
    );
    final rules = (currentRuleset?['rules'] as List?) ?? [];
    final query = _queryCtrl.text.trim().toLowerCase();

    final filteredRules = rules.where((r) {
      if (query.isEmpty) return true;
      final title = r['title']?.toString().toLowerCase() ?? '';
      final ref = r['legal_reference']?.toString().toLowerCase() ?? '';
      return title.contains(query) || ref.contains(query);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('LEGAL SOURCES & REPOSITORY',
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 1)),
        const SizedBox(height: 4),
        const Text('Versioned Rule Repository',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 2),
        const Text('Browse and verify versioned statutory rulesets implementing Legal Metrology regulations.',
            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
        const SizedBox(height: 18),

        // Controls
        Container(
          padding: const EdgeInsets.all(16),
          decoration: AppTheme.glassPanel(),
          child: Row(
            children: [
              // Ruleset dropdown
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _selected.isNotEmpty ? _selected : null,
                  decoration: const InputDecoration(labelText: 'Review Profile / Ruleset', isDense: true),
                  dropdownColor: const Color(0xFF131D31),
                  style: const TextStyle(fontSize: 12, color: Colors.white),
                  items: _items.map((i) {
                    final rid = i['ruleset_id']?.toString() ?? '';
                    return DropdownMenuItem(value: rid, child: Text(rid));
                  }).toList(),
                  onChanged: (v) => setState(() => _selected = v ?? ''),
                ),
              ),
              const SizedBox(width: 16),

              // Search
              Expanded(
                child: TextField(
                  controller: _queryCtrl,
                  onChanged: (_) => setState(() {}),
                  style: const TextStyle(fontSize: 12, color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Search rules',
                    hintText: 'Name or citation…',
                    prefixIcon: Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                    isDense: true,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Ruleset description
        if (currentRuleset != null && currentRuleset['description'] != null)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0x26F59E0B),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0x4DF59E0B)),
            ),
            child: Text(
              currentRuleset['description'].toString(),
              style: const TextStyle(fontSize: 12, color: Color(0xFFFEF3C7)),
            ),
          ),
        const SizedBox(height: 16),

        // Rules Grid
        if (_loading)
          const Padding(
            padding: EdgeInsets.all(48),
            child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
          )
        else if (filteredRules.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            decoration: AppTheme.glassPanel(),
            child: const Center(
              child: Text('No statutory rules matched your query.', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
            ),
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final isDesktop = constraints.maxWidth >= 800;
              final w = isDesktop ? (constraints.maxWidth - 14) / 2 : constraints.maxWidth;

              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: filteredRules.map((r) {
                  final title = r['title']?.toString() ?? '';
                  final ref = r['legal_reference']?.toString() ?? '';
                  final status = r['legal_status']?.toString().replaceAll('_', ' ') ?? '';
                  final declarations = (r['required_declaration_types'] as List?)?.join(', ') ?? '';
                  final sourceUrl = r['verification_metadata']?['source']?.toString();

                  return Container(
                    width: w,
                    padding: const EdgeInsets.all(16),
                    decoration: AppTheme.glassPanel(),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                        const SizedBox(height: 6),
                        Text(ref, style: const TextStyle(fontSize: 11, color: AppTheme.emerald)),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(4)),
                          child: Text(status, style: const TextStyle(fontSize: 9, color: Color(0xFFCBD5E1), fontFamily: 'monospace')),
                        ),
                        const SizedBox(height: 8),
                        Text('Required Evidence: $declarations', style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
                        if (sourceUrl != null && sourceUrl.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          InkWell(
                            onTap: () {
                              final uri = Uri.tryParse(sourceUrl);
                              if (uri != null) launchUrl(uri);
                            },
                            child: const Text('Official statutory source ↗',
                                style: TextStyle(fontSize: 11, color: AppTheme.cyan, decoration: TextDecoration.underline)),
                          ),
                        ],
                      ],
                    ),
                  );
                }).toList(),
              );
            },
          ),
      ],
    );
  }
}
