export function validatePhotos(files, existingCount = 0) {
  if (files.length + existingCount > 20) throw new Error('You can attach up to 20 photos. Remove a photo before adding more.')
  for (const file of files) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error(`${file.name}: choose a JPEG, PNG or WebP image.`)
    if (!file.size || file.size > 15 * 1024 * 1024) throw new Error(`${file.name}: choose a non-empty image smaller than 15 MB.`)
  }
}

export function scanNotice(batch) {
  if (batch.results?.some(run => /mock/i.test(run.engine_name))) throw new Error('The server is using demo OCR. Enable PaddleOCR to scan real package photos.')
  if (!batch.results?.some(run => ['SUCCESS', 'PARTIAL'].includes(run.status) && run.block_count > 0)) throw new Error('No readable text found. Try a sharper, well-lit photo, then scan again.')
  return batch.failed || batch.partial ? 'Some photos could not be read completely. Check the details and retake unclear photos.' : ''
}
