interface ProductCardProps {
  name: string
  price: number
}

export function ProductCard({ name, price }: ProductCardProps) {
  return (
    <article>
      <h3>{name}</h3>
      <p>₦{price.toLocaleString()}</p>
    </article>
  )
}
