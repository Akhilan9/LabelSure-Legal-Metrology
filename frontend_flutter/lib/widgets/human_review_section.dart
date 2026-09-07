import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class HumanReviewSection extends StatefulWidget {
  final Map<String, dynamic> inspection;
  final VoidCallback? onReviewUpdated;

  const HumanReviewSection({
    super.key,
    required this.inspection,
    this.onReviewUpdated,
  });

  @override
  State<HumanReviewSection> createState() => _HumanReviewSectionState();
}

class _HumanReviewSectionState extends State<HumanReviewSection> {
  Map<String, dynamic>? _review;
  bool _loading = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final id = widget.inspection['id'];
      final res = await ApiClient().get('/inspections/$id/review');
      if (mounted) {
        setState(() {
          _review = res is Map<String, dynamic> ? res : null;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showFinalizeDialog() {
    String selectedStatus = 'COMPLIANT';
    final notesCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF0F172A),
              title: const Text('Finalize Adjudication Review', style: TextStyle(color: Colors.white, fontSize: 14)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Select final official statutory compliance status:',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: selectedStatus,
                    dropdownColor: const Color(0xFF1E293B),
                    style: const TextStyle(fontSize: 11, color: Colors.white),
                    items: const [
                      DropdownMenuItem(value: 'COMPLIANT', child: Text('COMPLIANT (PASS)')),
                      DropdownMenuItem(value: 'NON_COMPLIANT', child: Text('NON-COMPLIANT (FAIL)')),
                      DropdownMenuItem(value: 'REVIEW_REQUIRED', child: Text('ATTENTION / REVIEW REQUIRED')),
                    ],
                    onChanged: (val) => setDialogState(() => selectedStatus = val ?? 'COMPLIANT'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: notesCtrl,
                    maxLines: 3,
                    style: const TextStyle(fontSize: 11, color: Colors.white),
                    decoration: const InputDecoration(
                      labelText: 'Summary Adjudication Notes',
                      hintText: 'Official rationale for court-admissible record…',
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Cancel', style: TextStyle(color: Color(0xFF94A3B8))),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.emerald),
                  onPressed: () async {
                    Navigator.of(ctx).pop();
                    setState(() => _saving = true);
                    try {
                      final id = widget.inspection['id'];
                      await ApiClient().post('/inspections/$id/review/finalize', body: {
                        'final_compliance_status': selectedStatus,
                        'summary_notes': notesCtrl.text.trim(),
                      });
                      await _load();
                      widget.onReviewUpdated?.call();
                    } catch (_) {}
                    if (mounted) setState(() => _saving = false);
                  },
                  child: const Text('Confirm & Seal Review', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showOverrideDialog(Map<String, dynamic> decision) {
    String verdict = decision['final_verdict']?.toString() ?? 'COMPLIANT';
    final reasonCtrl = TextEditingController(text: decision['override_reason']?.toString() ?? '');
    final notesCtrl = TextEditingController(text: decision['reviewer_notes']?.toString() ?? '');

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF0F172A),
              title: Text('Override Decision: ${decision['rule_key']}', style: const TextStyle(color: Colors.white, fontSize: 13)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: verdict,
                    dropdownColor: const Color(0xFF1E293B),
                    style: const TextStyle(fontSize: 11, color: Colors.white),
                    items: const [
                      DropdownMenuItem(value: 'COMPLIANT', child: Text('COMPLIANT')),
                      DropdownMenuItem(value: 'NON_COMPLIANT', child: Text('NON-COMPLIANT')),
                      DropdownMenuItem(value: 'UNCERTAIN', child: Text('UNCERTAIN')),
                    ],
                    onChanged: (val) => setDialogState(() => verdict = val ?? 'COMPLIANT'),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: reasonCtrl,
                    style: const TextStyle(fontSize: 11, color: Colors.white),
                    decoration: const InputDecoration(labelText: 'Justification Reason (Mandatory)'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: notesCtrl,
                    style: const TextStyle(fontSize: 11, color: Colors.white),
                    decoration: const InputDecoration(labelText: 'Internal Officer Notes'),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Cancel', style: TextStyle(color: Color(0xFF94A3B8))),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.emerald),
                  onPressed: () async {
                    if (reasonCtrl.text.trim().length < 5) return;
                    Navigator.of(ctx).pop();
                    setState(() => _saving = true);
                    try {
                      final id = widget.inspection['id'];
                      await ApiClient().post('/inspections/$id/review/rule-decisions', body: {
                        'rule_id': decision['rule_id'] ?? decision['rule_key'],
                        'rule_key': decision['rule_key'],
                        'final_verdict': verdict,
                        'override_reason': reasonCtrl.text.trim(),
                        'reviewer_notes': notesCtrl.text.trim(),
                      });
                      await _load();
                      widget.onReviewUpdated?.call();
                    } catch (_) {}
                    if (mounted) setState(() => _saving = false);
                  },
                  child: const Text('Save Decision', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isFinalized = _review?['status'] == 'FINALIZED';
    final decisions = (_review?['rule_decisions'] as List?) ?? [];

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'HUMAN OFFICER ADJUDICATION WORKSPACE',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: isFinalized ? const Color(0x3310B981) : const Color(0x33F59E0B),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            isFinalized ? 'FINALIZED & LOCKED' : 'REVIEW IN PROGRESS',
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                              color: isFinalized ? AppTheme.emerald : AppTheme.amber,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Statutory officer oversight with accountable overrides and tamper-evident audit sealing.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),

              if (!isFinalized)
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.emerald,
                    foregroundColor: const Color(0xFF090D16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  icon: const Icon(Icons.lock, size: 14),
                  label: const Text('Finalize Review', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                  onPressed: _saving ? null : _showFinalizeDialog,
                ),
            ],
          ),
          const SizedBox(height: 16),

          if (_loading)
            const Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2))
          else if (decisions.isEmpty)
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF131D31),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text('No rule decisions pending review. Run rule evaluation first.',
                    style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ),
            )
          else
            ...decisions.map((d) {
              final ruleKey = d['rule_key']?.toString() ?? '';
              final finalVerdict = d['final_verdict']?.toString() ?? 'COMPLIANT';
              final isOverride = d['is_overridden'] == true;

              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF131D31),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: isOverride ? AppTheme.amber : const Color(0xFF1E293B),
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(ruleKey, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white, fontFamily: 'monospace')),
                              if (isOverride) ...[
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                  decoration: BoxDecoration(
                                    color: const Color(0x33F59E0B),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text('HUMAN OVERRIDE', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.amber)),
                                ),
                              ],
                            ],
                          ),
                          if (d['override_reason'] != null) ...[
                            const SizedBox(height: 4),
                            Text('Reason: "${d['override_reason']}"', style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1), fontStyle: FontStyle.italic)),
                          ],
                        ],
                      ),
                    ),
                    Text(finalVerdict, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                    if (!isFinalized) ...[
                      const SizedBox(width: 12),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.emerald,
                          side: const BorderSide(color: Color(0x4D10B981)),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        ),
                        onPressed: () => _showOverrideDialog(d as Map<String, dynamic>),
                        child: const Text('Edit Decision', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}
