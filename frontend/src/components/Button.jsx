import React from 'react'

export default function Button({children, variant='primary', size='md', className='', ...props}){
  const sizeClass = size === 'sm' ? 'button-sm' : size === 'lg' ? 'button-lg' : 'button-md'
  const variantClass = variant === 'ghost' ? 'button-ghost' : variant === 'subtle' ? 'button-subtle' : variant === 'danger' ? 'button-danger' : 'button-primary'
  return (
    <button className={`button ${sizeClass} ${variantClass} ${className}`} {...props}>
      {children}
    </button>
  )
}
