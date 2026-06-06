const MAX_DIMENSION = 1600 // 가장 긴 변 기준 최대 픽셀
const JPEG_QUALITY = 0.82
const COMPRESS_THRESHOLD_BYTES = 1.2 * 1024 * 1024 // 1.2MB 초과 시에만 압축
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024 // 15MB 초과는 거부

export interface CompressResult {
  file: File
  error?: string
}

/**
 * 이미지 파일을 압축한다.
 * - 이미지가 아니거나 임계값 이하이면 원본 그대로 반환
 * - 15MB 초과면 error 반환(파일은 원본 유지)
 * - 브라우저 API 사용 불가/실패 시 원본 그대로 반환(안전)
 */
export async function compressImage(file: File): Promise<CompressResult> {
  if (!file.type.startsWith('image/')) return { file }
  if (file.size > MAX_UPLOAD_BYTES) {
    return { file, error: '이미지가 너무 큽니다 (최대 15MB). 더 작은 사진을 사용해 주세요.' }
  }
  if (file.size <= COMPRESS_THRESHOLD_BYTES) return { file }
  if (typeof document === 'undefined' || typeof createImageBitmap === 'undefined') return { file }

  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height))
    const targetW = Math.round(bitmap.width * scale)
    const targetH = Math.round(bitmap.height * scale)

    const canvas = document.createElement('canvas')
    canvas.width = targetW
    canvas.height = targetH
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      bitmap.close?.()
      return { file }
    }
    ctx.drawImage(bitmap, 0, 0, targetW, targetH)
    bitmap.close?.()

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), 'image/jpeg', JPEG_QUALITY)
    )
    if (!blob || blob.size >= file.size) return { file }

    const compressed = new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', {
      type: 'image/jpeg',
      lastModified: Date.now(),
    })
    return { file: compressed }
  } catch {
    return { file }
  }
}
