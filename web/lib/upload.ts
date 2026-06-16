// Server-side file upload validation shared across grade / chat / concept-cards routes.

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024 // 5 MB
const ALLOWED_MIME = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp'])

/** Validates magic bytes of an image buffer. Returns false for non-image files. */
export function isValidImageMagic(buf: Buffer): boolean {
  if (buf.length < 12) return false
  // JPEG: FF D8 FF
  if (buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) return true
  // PNG: 89 50 4E 47
  if (buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4e && buf[3] === 0x47) return true
  // GIF: 47 49 46 38
  if (buf[0] === 0x47 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x38) return true
  // WebP: RIFF....WEBP
  if (
    buf[0] === 0x52 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x46 &&
    buf[8] === 0x57 && buf[9] === 0x45 && buf[10] === 0x42 && buf[11] === 0x50
  ) return true
  return false
}

/**
 * Validates an uploaded file's size, MIME type, and magic bytes.
 * Returns an error string if invalid, null if OK.
 */
export function validateImageUpload(file: File, buf: Buffer): string | null {
  if (file.size > MAX_UPLOAD_BYTES) return '이미지는 5MB 이하만 업로드할 수 있습니다.'
  if (!ALLOWED_MIME.has(file.type)) return '이미지 파일(JPEG, PNG, GIF, WebP)만 업로드 가능합니다.'
  if (!isValidImageMagic(buf)) return '유효한 이미지 파일이 아닙니다.'
  return null
}
