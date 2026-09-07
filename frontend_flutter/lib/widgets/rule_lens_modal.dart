import 'package:flutter/material.dart';
import '../core/theme.dart';

class RuleLensExplanation {
  final String ruleKey;
  final String title;
  final String legalReference;
  final String legalStatus;
  final String verdict;
  final String reasonCode;
  final String severity;
  final double? evidenceConfidence;
  final String legalDisclaimer;
  final List<dynamic> decisionTrace;
  final List<dynamic> evidenceMap;
  final List<dynamic> counterfactualGuidance;
  final Map<String, dynamic>? legalPrecedents;

  RuleLensExplanation({
    required this.ruleKey,
    required this.title,
    required this.legalReference,
    required this.legalStatus,
    required this.verdict,
    required this.reasonCode,
    required this.severity,
    this.evidenceConfidence,
    required this.legalDisclaimer,
    required this.decisionTrace,
    required this.evidenceMap,
    required this.counterfactualGuidance,
    this.legalPrecedents,
  });

  factory RuleLensExplanation.fromJson(Map<String, dynamic> json) {
    return RuleLensExplanation(
      ruleKey: json['rule_key']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Statutory Rule',
      legalReference: json['legal_reference']?.toString() ?? '',
      legalStatus: json['legal_status']?.toString() ?? '',
      verdict: json['verdict']?.toString() ?? 'UNCERTAIN',
      reasonCode: json['reason_code']?.toString() ?? '',
      severity: json['severity']?.toString() ?? 'MEDIUM',
      evidenceConfidence: (json['evidence_confidence'] as num?)?.toDouble(),
      legalDisclaimer: json['legal_disclaimer']?.toString() ??
          'Statutory rule evaluations are machine-assisted determinations based on visible evidence.',
      decisionTrace: (json['decision_trace'] as List?) ?? [],
      evidenceMap: (json['evidence_map'] as List?) ?? [],
      counterfactualGuidance: (json['counterfactual_guidance'] as List?) ?? [],
      legalPrecedents: json['legal_precedents'] as Map<String, dynamic>?,
    );
  }
}

class RuleLensModal extends StatefulWidget {
  final RuleLensExplanation explanation;
  final VoidCallback onClose;
  final ValueChanged<String>? onSelectImage;

  const RuleLensModal({
    super.key,
    required this.explanation,
    required this.onClose,
    this.onSelectImage,
  });

  @override
  State<RuleLensModal> createState() => _RuleLensModalState();
}

class _RuleLensModalState extends State<RuleLensModal> {
  String _activeTab = 'trace'; // trace, evidence, guidance, legal

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
        return const Color(0xFF94A3B8);
    }
  }

  @override
  Widget build(BuildContext context) {
    final exp = widget.explanation;
    final verdictColor = _getVerdictColor(exp.verdict);

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(16),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 850),
        height: 620,
        decoration: BoxDecoration(
          color: const Color(0xFF0D1527),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.borderSubtle),
          boxShadow: const [
            BoxShadow(color: Colors.black87, blurRadius: 30, offset: Offset(0, 10)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Bar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: Color(0xFF080D19),
                borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0x3310B981),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.4)),
                              ),
                              child: const Text(
                                'RuleLens Explainability',
                                style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              exp.ruleKey,
                              style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF94A3B8)),
                            ),
                            if (exp.legalStatus == 'PROTOTYPE_RULE') ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                decoration: BoxDecoration(
                                  color: const Color(0x33F59E0B),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: const Text(
                                  'PROTOTYPE',
                                  style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.amber),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          exp.title,
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                        Text(
                          exp.legalReference,
                          style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white, size: 20),
                    onPressed: widget.onClose,
                  ),
                ],
              ),
            ),

            // Verdict Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              color: const Color(0xFF131D31),
              child: Row(
                children: [
                  const Text('Statutory Verdict: ', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: verdictColor.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: verdictColor.withValues(alpha: 0.5)),
                    ),
                    child: Text(
                      exp.verdict.replaceAll('_', ' '),
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: verdictColor),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '[${exp.reasonCode}]',
                    style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF64748B)),
                  ),
                  const Spacer(),
                  Text(
                    'Severity: ${exp.severity} · Conf: ${exp.evidenceConfidence != null ? '${(exp.evidenceConfidence! * 100).toStringAsFixed(0)}%' : 'N/A'}',
                    style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                  ),
                ],
              ),
            ),

            // Legal Disclaimer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              color: const Color(0xFF0E1626),
              child: Text(
                '⚖️ ${exp.legalDisclaimer}',
                style: const TextStyle(fontSize: 10, fontStyle: FontStyle.italic, color: Color(0xFF94A3B8)),
              ),
            ),

            // Tabs Selector
            Container(
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
                color: Color(0xFF131D31),
              ),
              child: Row(
                children: [
                  _buildTabButton('trace', '🔍 Decision Trace Pipeline'),
                  _buildTabButton('evidence', '📦 Evidence Provenance Map'),
                  _buildTabButton('guidance', '💡 Counterfactual Guidance'),
                  _buildTabButton('legal', '📜 Legal Precedents & Rules'),
                ],
              ),
            ),

            // Tab Content
            Expanded(
              child: Container(
                color: const Color(0xFF0B132B),
                padding: const EdgeInsets.all(16),
                child: _buildTabContent(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTabButton(String key, String label) {
    final active = _activeTab == key;
    return InkWell(
      onTap: () => setState(() => _activeTab = key),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: active ? AppTheme.emerald : Colors.transparent,
              width: 2,
            ),
          ),
          color: active ? const Color(0x1A10B981) : Colors.transparent,
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: active ? FontWeight.bold : FontWeight.normal,
            color: active ? AppTheme.emerald : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }

  Widget _buildTabContent() {
    switch (_activeTab) {
      case 'trace':
        return _buildTraceTab();
      case 'evidence':
        return _buildEvidenceTab();
      case 'guidance':
        return _buildGuidanceTab();
      case 'legal':
      default:
        return _buildLegalTab();
    }
  }

  Widget _buildTraceTab() {
    final steps = widget.explanation.decisionTrace;
    if (steps.isEmpty) {
      return const Center(
        child: Text('No decision trace steps recorded for this rule.', style: TextStyle(color: Color(0xFF64748B))),
      );
    }

    return ListView.separated(
      itemCount: steps.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        final step = steps[i] as Map<String, dynamic>;
        final stepVerdict = step['verdict']?.toString() ?? 'PASS';
        final isPass = ['PASS', 'PASSED', 'COMPLIANT'].contains(stepVerdict.toUpperCase());

        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF131D31),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isPass ? const Color(0x3310B981) : const Color(0x33F43F5E),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isPass ? '✓' : '✗',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isPass ? AppTheme.emerald : AppTheme.rose,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      step['step_name']?.toString() ?? 'Pipeline Step ${i + 1}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      step['explanation']?.toString() ?? step['reason']?.toString() ?? 'Evaluated according to statutory criteria.',
                      style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                    if (step['evaluated_value'] != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Value: ${step['evaluated_value']} (Threshold: ${step['expected_threshold'] ?? 'Standard'})',
                        style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFFCBD5E1)),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEvidenceTab() {
    final evidence = widget.explanation.evidenceMap;
    if (evidence.isEmpty) {
      return const Center(
        child: Text('No evidence coordinates linked to this finding.', style: TextStyle(color: Color(0xFF64748B))),
      );
    }

    return ListView.builder(
      itemCount: evidence.length,
      itemBuilder: (context, index) {
        final ev = evidence[index] as Map<String, dynamic>;
        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF131D31),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Source Declaration: ${ev['declaration_type'] ?? 'Evidence Panel'}',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.emerald),
              ),
              const SizedBox(height: 4),
              Text(
                'Matched Text: "${ev['raw_text'] ?? ev['normalized_value'] ?? ''}"',
                style: const TextStyle(fontSize: 11, color: Colors.white),
              ),
              const SizedBox(height: 4),
              Text(
                'Panel: ${ev['panel_type'] ?? 'FRONT'} · Confidence: ${((ev['confidence'] ?? 0.8) * 100).toStringAsFixed(0)}%',
                style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontFamily: 'monospace'),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildGuidanceTab() {
    final guidance = widget.explanation.counterfactualGuidance;
    if (guidance.isEmpty) {
      return const Center(
        child: Text('No counterfactual remediations needed. Package complies with statutory requirement.',
            style: TextStyle(color: AppTheme.emerald, fontSize: 12)),
      );
    }

    return ListView.builder(
      itemCount: guidance.length,
      itemBuilder: (context, i) {
        final item = guidance[i];
        final text = item is Map ? (item['guidance'] ?? item['remedy'] ?? item.toString()) : item.toString();
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0x1AF59E0B),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0x40F59E0B)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('💡', style: TextStyle(fontSize: 14)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(text, style: const TextStyle(fontSize: 11, color: Colors.white, height: 1.4)),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildLegalTab() {
    final legal = widget.explanation.legalPrecedents ?? {};
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF131D31),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Statutory Citation & Authority',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white)),
                const SizedBox(height: 6),
                Text(widget.explanation.legalReference,
                    style: const TextStyle(fontSize: 11, color: AppTheme.emerald)),
                const SizedBox(height: 8),
                const Text(
                  'Legal Metrology (Packaged Commodities) Rules, 2011 (as amended 2021-2026). Mandatory declarations under Rule 6 and packaging standards under Chapter II.',
                  style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF131D31),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Penalty & Statutory Action Under Act',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white)),
                const SizedBox(height: 6),
                Text(
                  legal['penalty']?.toString() ??
                      'Section 36(1) of the Legal Metrology Act, 2009: Non-compliance with packaging declarations attracts fines up to ₹25,000 for first offence, ₹50,000 for second offence, and up to ₹1,00,000 or imprisonment up to one year for subsequent offences.',
                  style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1), height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
