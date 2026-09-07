import 'package:flutter/material.dart';
import '../core/theme.dart';

class InspectionWorkflowStepper extends StatelessWidget {
  final Map<String, dynamic> inspection;
  final Map<String, dynamic>? ocrSummary;
  final bool hasQuality;
  final bool hasExtraction;
  final bool hasContext;
  final bool hasEvaluation;
  final bool hasReview;
  final VoidCallback? onRunQuality;
  final VoidCallback? onRunOCR;
  final VoidCallback? onExtract;
  final ValueChanged<String>? onScrollToSection;

  const InspectionWorkflowStepper({
    super.key,
    required this.inspection,
    this.ocrSummary,
    this.hasQuality = false,
    this.hasExtraction = false,
    this.hasContext = false,
    this.hasEvaluation = false,
    this.hasReview = false,
    this.onRunQuality,
    this.onRunOCR,
    this.onExtract,
    this.onScrollToSection,
  });

  @override
  Widget build(BuildContext context) {
    final imagesCount = inspection['images_count'] ?? (inspection['images'] as List?)?.length ?? 0;
    final hasImages = imagesCount > 0;
    final hasOcr = (ocrSummary?['total_blocks'] ?? 0) > 0;

    final steps = [
      (title: 'Capture Evidence', done: hasImages, section: 'evidence-section'),
      (title: 'Quality Assessment', done: hasQuality, section: 'evidence-section'),
      (title: 'PaddleOCR Extraction', done: hasOcr, section: 'evidence-section'),
      (title: 'Declaration Extraction', done: hasExtraction, section: 'extraction-section'),
      (title: 'Context & Applicability', done: hasContext, section: 'context-section'),
      (title: 'Legal Rules Evaluation', done: hasEvaluation, section: 'evaluation-section'),
      (title: 'Officer Adjudication', done: hasReview, section: 'review-section'),
      (title: 'PDF & Audit Trail', done: inspection['status'] == 'COMPLIANT' || inspection['status'] == 'NON_COMPLIANT', section: 'reports-section'),
    ];

    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Text('REGULATORY PROGRESSION STEPPER',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
              Spacer(),
              Text('LMPC 2011–2026 Audit Standard',
                  style: TextStyle(fontSize: 10, color: Color(0xFF64748B), fontFamily: 'monospace')),
            ],
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: steps.asMap().entries.map((entry) {
                final idx = entry.key;
                final step = entry.value;
                final isLast = idx == steps.length - 1;

                return Row(
                  children: [
                    InkWell(
                      onTap: () => onScrollToSection?.call(step.section),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: step.done ? const Color(0x2610B981) : const Color(0xFF131D31),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: step.done ? const Color(0x4D10B981) : const Color(0xFF1E293B),
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 18,
                              height: 18,
                              decoration: BoxDecoration(
                                color: step.done ? AppTheme.emerald : const Color(0xFF334155),
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: Text(
                                  step.done ? '✓' : '${idx + 1}',
                                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.white),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              step.title,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: step.done ? FontWeight.bold : FontWeight.normal,
                                color: step.done ? AppTheme.emerald : const Color(0xFF94A3B8),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (!isLast)
                      Container(
                        width: 16,
                        height: 1.5,
                        color: step.done ? const Color(0x4D10B981) : const Color(0xFF1E293B),
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
}
