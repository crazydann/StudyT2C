import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'StudyT2C - 스마트 학습 도우미',
  description: '한국 중·고등학생을 위한 AI 기반 학습 튜터링 서비스',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="preconnect"
          href="https://cdn.jsdelivr.net"
          crossOrigin="anonymous"
        />
      </head>
      <body className="font-pretendard antialiased">
        {children}
      </body>
    </html>
  )
}
