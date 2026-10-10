import React from 'react';
import './Skeleton.css';

/**
 * Base generic Skeleton element with shimmer
 */
export function Skeleton({ width, height, borderRadius, style = {}, className = '' }) {
  const inlineStyles = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
    ...(borderRadius ? { borderRadius } : {}),
    ...style,
  };

  return (
    <div
      className={`skeleton-box skeleton-shimmer ${className}`}
      style={inlineStyles}
      aria-hidden="true"
    />
  );
}

/**
 * 1. ProductCardSkeleton - for Menu page during fetch
 */
export function ProductCardSkeleton() {
  return (
    <div className="product-card-skeleton" aria-label="Loading product">
      <div className="skeleton-img-box skeleton-shimmer">
        <div className="skeleton-badge skeleton-shimmer" />
      </div>
      <div className="skeleton-info">
        <div className="skeleton-line-title skeleton-shimmer" />
        <div className="skeleton-line-price skeleton-shimmer" />
        <div className="skeleton-qty-box skeleton-shimmer" />
        <div className="skeleton-btn-box skeleton-shimmer" />
      </div>
    </div>
  );
}

export function ProductSkeletonGrid({ count = 8 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <ProductCardSkeleton key={`product-skel-${index}`} />
      ))}
    </>
  );
}

/**
 * 2. CanteenChoiceSkeleton - for Home page canteen choices
 */
export function CanteenChoiceSkeleton({ count = 3 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <li key={`canteen-skel-${index}`} style={{ listStyle: 'none', width: '100%' }}>
          <div className="canteen-choice-skeleton skeleton-shimmer">
            <div className="skeleton-text-inner" />
          </div>
        </li>
      ))}
    </>
  );
}

/**
 * 3. CartItemSkeleton & List - for Cart page
 */
export function CartItemSkeleton() {
  return (
    <div className="cart-card-skeleton" aria-label="Loading cart item">
      <div className="skeleton-cart-img skeleton-shimmer" />
      <div className="skeleton-cart-info">
        <div className="skeleton-cart-title skeleton-shimmer" />
        <div className="skeleton-cart-price skeleton-shimmer" />
        <div className="skeleton-cart-actions">
          <div className="skeleton-cart-qty skeleton-shimmer" />
          <div className="skeleton-cart-remove skeleton-shimmer" />
        </div>
      </div>
    </div>
  );
}

export function CartSkeletonList({ count = 3 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <CartItemSkeleton key={`cart-skel-${index}`} />
      ))}
    </>
  );
}

export function CartSummarySkeleton() {
  return (
    <div className="cart-summary-skeleton" aria-label="Loading order summary">
      <div className="skeleton-summary-title skeleton-shimmer" />
      <div className="skeleton-summary-row">
        <div className="skeleton-summary-label skeleton-shimmer" />
        <div className="skeleton-summary-val skeleton-shimmer" />
      </div>
      <div className="skeleton-summary-row">
        <div className="skeleton-summary-label skeleton-shimmer" />
        <div className="skeleton-summary-val skeleton-shimmer" />
      </div>
      <hr style={{ border: 'none', borderTop: '1px solid #f0f0f0', margin: '8px 0' }} />
      <div className="skeleton-summary-row">
        <div className="skeleton-summary-label skeleton-shimmer" style={{ width: '40%' }} />
        <div className="skeleton-summary-val skeleton-shimmer" style={{ width: '30%' }} />
      </div>
      <div className="skeleton-summary-btn skeleton-shimmer" />
    </div>
  );
}

/**
 * 4. OrderCardSkeleton - for Orders page
 */
export function OrderCardSkeleton() {
  return (
    <div className="order-card-skeleton" aria-label="Loading order">
      <div className="skeleton-order-header">
        <div className="skeleton-order-canteen skeleton-shimmer" />
        <div className="skeleton-order-id skeleton-shimmer" />
        <div className="skeleton-order-date skeleton-shimmer" />
      </div>
      <div className="skeleton-order-items">
        <div className="skeleton-item-line-1 skeleton-shimmer" />
        <div className="skeleton-item-line-2 skeleton-shimmer" />
      </div>
      <div className="skeleton-order-footer">
        <div className="skeleton-order-total skeleton-shimmer" />
        <div className="skeleton-order-badge skeleton-shimmer" />
      </div>
      <div className="skeleton-order-btn skeleton-shimmer" />
    </div>
  );
}

export function OrderSkeletonGrid({ count = 6 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <OrderCardSkeleton key={`order-skel-${index}`} />
      ))}
    </>
  );
}

/**
 * 5. AdminOrderCardSkeleton - for Admin pending/preparing/delivered boards
 */
export function AdminOrderCardSkeleton() {
  return (
    <div className="admin-order-skeleton" aria-label="Loading admin order">
      <div className="skeleton-admin-order-id skeleton-shimmer" />
      <div className="skeleton-admin-canteen skeleton-shimmer" />
      <div className="skeleton-admin-items skeleton-shimmer" />
      <div className="skeleton-admin-btn skeleton-shimmer" />
    </div>
  );
}

export function AdminOrderSkeletonGrid({ count = 6 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <AdminOrderCardSkeleton key={`admin-order-skel-${index}`} />
      ))}
    </>
  );
}

/**
 * 6. AdminMenuCardSkeleton - for Admin Manage Menu tab
 */
export function AdminMenuCardSkeleton() {
  return (
    <div className="admin-menu-skeleton-card" aria-label="Loading menu item">
      <div className="skeleton-admin-img skeleton-shimmer" />
      <div className="skeleton-admin-body">
        <div className="skeleton-admin-title skeleton-shimmer" />
        <div className="skeleton-admin-price skeleton-shimmer" />
        <div className="skeleton-admin-stock-row skeleton-shimmer" />
        <div className="skeleton-admin-actions-row">
          <div className="skeleton-shimmer" />
          <div className="skeleton-shimmer" />
          <div className="skeleton-shimmer" />
        </div>
      </div>
    </div>
  );
}

export function AdminMenuSkeletonGrid({ count = 6 }) {
  return (
    <div className="admin-menu-grid">
      {Array.from({ length: count }).map((_, index) => (
        <AdminMenuCardSkeleton key={`admin-menu-skel-${index}`} />
      ))}
    </div>
  );
}

/**
 * 7. AdminAuthSkeleton - for Admin authentication checking state
 */
export function AdminAuthSkeleton() {
  return (
    <div className="admin-auth-skeleton-wrap">
      <div className="admin-auth-skeleton-header skeleton-shimmer" />
      <div className="admin-auth-skeleton-tabs">
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
        <div className="admin-auth-skeleton-tab skeleton-shimmer" />
      </div>
      <div className="order-board" style={{ marginTop: '20px' }}>
        <AdminOrderSkeletonGrid count={6} />
      </div>
    </div>
  );
}
