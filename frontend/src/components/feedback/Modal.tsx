interface ModalProps {
  title: string
  children: React.ReactNode
}

export function Modal({ title, children }: ModalProps) {
  return (
    <section aria-label={title}>
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  )
}
