import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy, computed, inject, signal } from '@angular/core';
import { Observable, Subject } from 'rxjs';

import {
  CheckPriceResponse,
  CheckStatusOut,
  PriceCheckRow,
  PriceRecord,
  PriceUpdateEvent,
} from '../models/price.model';

const API_BASE = '/api/v1';

@Injectable({ providedIn: 'root' })
export class PriceStreamService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private eventSource: EventSource | null = null;

  /** Live map of requestId -> latest known row, exposed as a read-only Signal. */
  private readonly rowsMap = signal<Map<string, PriceCheckRow>>(new Map());
  readonly rows = computed(() =>
    Array.from(this.rowsMap().values()).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  );

  readonly connectionStatus = signal<'connecting' | 'open' | 'closed' | 'error'>('closed');

  /** Emits every raw PriceUpdated event, for components that want the stream directly. */
  private readonly updates$ = new Subject<PriceUpdateEvent>();
  readonly onUpdate$: Observable<PriceUpdateEvent> = this.updates$.asObservable();

  connect(): void {
    if (this.eventSource) {
      return;
    }
    this.connectionStatus.set('connecting');
    this.eventSource = new EventSource(`${API_BASE}/prices/stream`);

    this.eventSource.addEventListener('open', () => this.connectionStatus.set('open'));

    this.eventSource.addEventListener('price-update', (event: MessageEvent) => {
      try {
        const payload: PriceUpdateEvent = JSON.parse(event.data);
        this.applyUpdate(payload);
        this.updates$.next(payload);
      } catch (err) {
        console.error('Failed to parse price-update SSE payload', err);
      }
    });

    this.eventSource.addEventListener('error', () => {
      this.connectionStatus.set('error');
      // EventSource auto-reconnects on transient errors; explicit close()
      // is only needed when the caller navigates away (see disconnect()).
    });
  }

  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
    this.connectionStatus.set('closed');
  }

  triggerCheck(productUrl: string): Observable<CheckPriceResponse> {
    const optimisticRow: PriceCheckRow = {
      requestId: '',
      productUrl,
      productTitle: null,
      priceAmount: null,
      currency: 'INR',
      inStock: true,
      promoText: null,
      status: 'pending',
      errorMessage: null,
      updatedAt: new Date().toISOString(),
    };
    return new Observable<CheckPriceResponse>((subscriber) => {
      this.http.post<CheckPriceResponse>(`${API_BASE}/check-price`, { product_url: productUrl }).subscribe({
        next: (res) => {
          const row: PriceCheckRow = { ...optimisticRow, requestId: res.request_id, status: res.status };
          this.upsertRow(row);
          subscriber.next(res);
          subscriber.complete();
        },
        error: (err) => subscriber.error(err),
      });
    });
  }

  getCheckStatus(requestId: string): Observable<CheckStatusOut> {
    return this.http.get<CheckStatusOut>(`${API_BASE}/check-price/${requestId}`);
  }

  getHistory(productUrl: string, limit = 50): Observable<PriceRecord[]> {
    return this.http.get<PriceRecord[]>(`${API_BASE}/prices/history`, {
      params: { product_url: productUrl, limit },
    });
  }

  private applyUpdate(payload: PriceUpdateEvent): void {
    const row: PriceCheckRow = {
      requestId: payload.request_id,
      productUrl: payload.product_url,
      productTitle: payload.product_title,
      priceAmount: payload.price_amount,
      currency: payload.currency,
      inStock: payload.in_stock,
      promoText: payload.promo_text,
      status: payload.status,
      errorMessage: payload.error_message,
      updatedAt: payload.scraped_at,
    };
    this.upsertRow(row);
  }

  private upsertRow(row: PriceCheckRow): void {
    this.rowsMap.update((current) => {
      const next = new Map(current);
      next.set(row.requestId, row);
      return next;
    });
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
