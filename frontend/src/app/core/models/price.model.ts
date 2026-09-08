export type CheckStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface CheckPriceResponse {
  request_id: string;
  status: CheckStatus;
  message: string;
}

export interface CheckStatusOut {
  id: string;
  product_url: string;
  status: CheckStatus;
  requested_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface PriceRecord {
  id: string;
  product_url: string;
  product_title: string | null;
  price_amount: number;
  currency: string;
  in_stock: boolean;
  promo_text: string | null;
  scraped_at: string;
}

/** Shape of the raw event relayed verbatim over the SSE `price-update` stream. */
export interface PriceUpdateEvent {
  request_id: string;
  product_url: string;
  product_title: string | null;
  price_amount: number | null;
  currency: string;
  in_stock: boolean;
  promo_text: string | null;
  status: CheckStatus;
  error_message: string | null;
  scraped_at: string;
}

/** Client-side view-model row rendered in the dashboard table. */
export interface PriceCheckRow {
  requestId: string;
  productUrl: string;
  productTitle: string | null;
  priceAmount: number | null;
  currency: string;
  inStock: boolean;
  promoText: string | null;
  status: CheckStatus;
  errorMessage: string | null;
  updatedAt: string;
}
