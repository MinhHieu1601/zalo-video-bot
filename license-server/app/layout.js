export const metadata = {
  title: 'License Admin',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui', margin: 0 }}>{children}</body>
    </html>
  )
}
