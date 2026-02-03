"""
Seed script to create Sharp Picks products in Stripe.
Run this once to set up your subscription product.
Usage: python seed_products.py
"""
from stripe_client import get_stripe_client

def create_products():
    stripe = get_stripe_client()
    
    existing = stripe.Product.search(query="name:'Sharp Picks Premium'")
    if existing.data:
        print('Sharp Picks Premium already exists')
        print(f'Product ID: {existing.data[0].id}')
        prices = stripe.Price.list(product=existing.data[0].id, active=True)
        for price in prices.data:
            print(f'Price ID: {price.id} - ${price.unit_amount/100}/month')
        return
    
    product = stripe.Product.create(
        name='Sharp Picks Premium',
        description='Full access to all NBA betting predictions with 79%+ accuracy',
        metadata={
            'features': 'All predictions,Bet tracking,Performance analytics',
            'trial_days': '7'
        }
    )
    print(f'Created product: {product.id}')
    
    monthly_price = stripe.Price.create(
        product=product.id,
        unit_amount=2999,
        currency='usd',
        recurring={'interval': 'month'},
        metadata={'plan': 'monthly'}
    )
    print(f'Created monthly price: {monthly_price.id} ($29.99/month)')
    
    yearly_price = stripe.Price.create(
        product=product.id,
        unit_amount=19999,
        currency='usd',
        recurring={'interval': 'year'},
        metadata={'plan': 'yearly', 'savings': '44%'}
    )
    print(f'Created yearly price: {yearly_price.id} ($199.99/year)')

if __name__ == '__main__':
    create_products()
