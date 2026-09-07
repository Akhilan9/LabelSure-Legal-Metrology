import test from 'node:test'
import assert from 'node:assert/strict'
import { scanNotice, validatePhotos } from './scan.js'
const photo = { name: 'label.jpg', type: 'image/jpeg', size: 1024 }
test('validates the entire selection before creating a draft', () => {
  assert.doesNotThrow(() => validatePhotos([photo], 19))
  assert.throws(() => validatePhotos([photo], 20), /20 photos/)
  assert.throws(() => validatePhotos([{ ...photo, type: 'image/heic' }]), /JPEG/)
  assert.throws(() => validatePhotos([{ ...photo, size: 0 }]), /non-empty/)
  assert.throws(() => validatePhotos([{ ...photo, size: 16 * 1024 * 1024 }]), /15 MB/)
})
test('never treats mock or unreadable results as real scans', () => {
  assert.throws(() => scanNotice({ results: [{ engine_name: 'MockOCR', status: 'SUCCESS', block_count: 8 }] }), /demo OCR/)
  assert.throws(() => scanNotice({ results: [{ engine_name: 'PaddleOCR', status: 'FAILED', block_count: 0 }] }), /No readable text/)
  assert.throws(() => scanNotice({ results: [{ status: 'SUCCESS', block_count: 0 }] }), /No readable text/)
})
test('partial scans surface a warning and usable scans continue', () => {
  const results = [{ engine_name: 'PaddleOCR', status: 'SUCCESS', block_count: 8 }]
  assert.equal(scanNotice({ results }), '')
  assert.match(scanNotice({ results, failed: 1 }), /could not be read/)
})
