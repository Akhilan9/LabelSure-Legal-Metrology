import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_client.dart';
import '../core/theme.dart';
import 'rule_lens_modal.dart';

class RuleComplianceSection extends StatefulWidget {
  final Map<String, dynamic> inspection;
  final VoidCallback? onEvaluationComplete;

  const RuleComplianceSection({
    super.key,
    required this.inspection,
    this.onEvaluationComplete,
  });

  @override
  State<RuleComplianceSection> createState() => _RuleComplianceSectionState();
}

class _RuleComplianceSectionState extends State<RuleComplianceSection> {
  Map<String, dynamic>? _summary;
  List<dynamic> _results = [];
  bool _loading = false;
  bool _evaluating = false;
  bool _allowPrototypes = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final id = widget.inspection['id'];
      final sRes = await ApiClient().get('/inspections/$id/evaluation');
      final rRes = await ApiClient().get('/inspections/$id/evaluation/results');
      if (mounted) {
        setState(() {
          _summary = sRes is Map<String, dynamic> ? sRes : null;
          _results = rRes is List ? rRes : [];
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _evaluate() async {
    setState(() => _evaluating = true);
    try {
      final id = widget.inspection['id'];
      await ApiClient().post('/inspections/$id/evaluate', body: {
        'allow_prototype_rules': _allowPrototypes,
      });
      await _load();
      widget.onEvaluationComplete?.call();
    } catch (_) {}
    if (mounted) setState(() => _evaluating = false);
  }

  Future<void> _openRuleLens(String ruleKey) async {
    try {
      final id = widget.inspection['id'];
      final data = await ApiClient().get('/inspections/$id/rules/$ruleKey/explanation');
      if (data is Map<String, dynamic> && mounted) {
        final explanation = RuleLensExplanation.fromJson(data);
        showDialog(
          context: context,
          builder: (ctx) => RuleLensModal(
            explanation: explanation,
            onClose: () => Navigator.of(ctx).pop(),
          ),
        );
      }
    } catch (_) {}
  }

  Color _getVerdictColor(String verdict) {
    switch (verdict.toUpperCase()) {
      case 'PASS':
      case 'COMPLIANT':
        return AppTheme.emerald;
      case 'FAIL':
      case 'NON_COMPLIANT':
        return AppTheme.rose;
      case 'UNCERTAIN':
        return AppTheme.amber;
      default:
        return const Color(0xFF64748B);
    }
  }

  @override
  Widget build(BuildContext context) {
    final overall = _summary?['overall']?.toString() ?? 'PENDING';
    final overallColor = _getVerdictColor(overall);

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header & Controls
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'LEGAL METROLOGY STATUTORY RULE EVALUATION',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0x3310B981),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text('Phase 8 Engine',
                              style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Deterministic statutory verification against the Legal Metrology (Packaged Commodities) Rules, 2011.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),

              Row(
                children: [
                  Row(
                    children: [
                      Checkbox(
                        value: _allowPrototypes,
                        activeColor: AppTheme.emerald,
                        onChanged: (v) => setState(() => _allowPrototypes = v ?? true),
                      ),
                      const Text('Allow Prototypes', style: TextStyle(fontSize: 11, color: Color(0xFFCBD5E1))),
                    ],
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.emerald,
                      foregroundColor: const Color(0xFF090D16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    icon: _evaluating
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Icon(Icons.gavel, size: 16),
                    label: Text(_evaluating ? 'Evaluating…' : '⚡ Run Statutory Verification',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    onPressed: _evaluating ? null : _evaluate,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Summary Scorecard
          if (_summary != null) ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildScoreTile('OVERALL VERDICT', overall, overallColor, isBadge: true),
                _buildScoreTile('RULES EVALUATED', '${_summary!['total_rules'] ?? _results.length}', Colors.white),
                _buildScoreTile('PASSED', '${_summary!['passed_count'] ?? 0}', AppTheme.emerald),
                _buildScoreTile('VIOLATIONS', '${_summary!['violations_count'] ?? 0}', AppTheme.rose),
                _buildScoreTile('REVIEW NEEDED', '${_summary!['uncertain_count'] ?? 0}', AppTheme.amber),
              ],
            ),
            const SizedBox(height: 16),
          ],

          // Legal Metrology Guideline Failure Justifications
          if (_summary != null) ...[
            Builder(
              builder: (context) {
                final rawList = _summary!['guideline_failure_justifications'] as List?;
                final justifications = (rawList != null && rawList.isNotEmpty)
                    ? rawList.map((e) => e.toString()).toList()
                    : <String>[];
                if (justifications.isEmpty) return const SizedBox.shrink();
                return Column(
                  children: [
                    _buildFailureJustificationsCard(justifications),
                    const SizedBox(height: 16),
                  ],
                );
              },
            ),
          ],

          if (_loading)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2)),
            )
          else if (_results.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF131D31),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text(
                  'No rule evaluations executed yet. Click "⚡ Run Statutory Verification" above.',
                  style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                ),
              ),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowHeight: 38,
                dataRowMinHeight: 48,
                dataRowMaxHeight: 58,
                columnSpacing: 18,
                headingTextStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B)),
                columns: const [
                  DataColumn(label: Text('RULE KEY / CITATION')),
                  DataColumn(label: Text('STATUTORY RULE NAME')),
                  DataColumn(label: Text('VERDICT')),
                  DataColumn(label: Text('SEVERITY')),
                  DataColumn(label: Text('EXPLAINABILITY')),
                ],
                rows: _results.map((r) {
                  final key = r['rule_key']?.toString() ?? '';
                  final title = r['title']?.toString() ?? '';
                  final ref = r['legal_reference']?.toString() ?? '';
                  final verdict = r['verdict']?.toString() ?? 'UNCERTAIN';
                  final severity = r['severity']?.toString() ?? 'MEDIUM';
                  final verdictColor = _getVerdictColor(verdict);

                  return DataRow(
                    cells: [
                      DataCell(Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(key, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: Colors.white)),
                          Text(ref, style: const TextStyle(fontSize: 9, color: Color(0xFF64748B))),
                        ],
                      )),
                      DataCell(ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 320),
                        child: Text(title, style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1)), maxLines: 2, overflow: TextOverflow.ellipsis),
                      )),
                      DataCell(Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: verdictColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: verdictColor.withValues(alpha: 0.4)),
                        ),
                        child: Text(verdict, style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: verdictColor)),
                      )),
                      DataCell(Text(severity, style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)))),
                      DataCell(
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0x3310B981),
                            foregroundColor: AppTheme.emerald,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                          icon: const Icon(Icons.visibility, size: 12),
                          label: const Text('RuleLens', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                          onPressed: () => _openRuleLens(key),
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

  Widget _buildScoreTile(String label, String value, Color color, {bool isBadge = false}) {
    return Container(
      width: 130,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF131D31),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
          const SizedBox(height: 4),
          if (isBadge)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: color.withValues(alpha: 0.5)),
              ),
              child: Text(value, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color)),
            )
          else
            Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color, fontFamily: 'monospace')),
        ],
      ),
    );
  }

  Widget _buildFailureJustificationsCard(List<String> justifications) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E1014),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0x80F43F5E), width: 1.5),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0x33F43F5E),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(Icons.warning_amber_rounded, color: AppTheme.rose, size: 18),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'Legal Metrology Guideline Failure Justifications',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Statutory non-compliance justifications under PCR Rule 6(1) & Legal Metrology Act, 2009',
                        style: TextStyle(fontSize: 10, color: Color(0xFFCBD5E1)),
                      ),
                    ],
                  ),
                ],
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFFECDD3),
                  side: const BorderSide(color: Color(0x66F43F5E)),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                ),
                icon: const Icon(Icons.copy, size: 12),
                label: const Text('Copy All', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
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
          const SizedBox(height: 12),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: justifications.length,
            separatorBuilder: (_, _) => const SizedBox(height: 6),
            itemBuilder: (context, index) {
              final item = justifications[index];
              return Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0x66F43F5E)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 2, right: 6),
                      child: Icon(Icons.error_outline, size: 13, color: AppTheme.rose),
                    ),
                    Expanded(
                      child: SelectableText(
                        item,
                        style: const TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: Color(0xFFFECDD3),
                          height: 1.4,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 13, color: Color(0xFFFDA4AF)),
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
}
