interface ProductCardProps {
  name: string
  price: number
  description?: string | null
  isAvailable?: boolean
}

export function ProductCard({ name, price, description, isAvailable = true }: ProductCardProps) {
  return (
    <article className="product-card">
      <div className="product-card__header">
        <h3>{name}</h3>
        <span className={isAvailable ? 'status-badge status-badge--active' : 'status-badge status-badge--muted'}>
          {isAvailable ? 'Available' : 'Unavailable'}
        </span>
      </div>
      {description ? <p className="product-card__description">{description}</p> : null}
      <p className="product-card__price">₦{price.toLocaleString()}</p>
    </article>
  )
}
