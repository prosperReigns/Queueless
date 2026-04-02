interface ProductCardProps {
  name: string
  price: string
}

export function ProductCard({ name, price }: ProductCardProps) {
  return (
    <article>
      <h3>{name}</h3>
      <p>{price}</p>
    </article>
  )
}
