import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';

import { PriceCheckRow, PriceRecord } from '../../core/models/price.model';
import { PriceStreamService } from '../../core/services/price-stream.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private readonly priceStream = inject(PriceStreamService);

  readonly urlControl = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^https?:\/\/.+/)],
  });

  readonly rows = this.priceStream.rows;
  readonly connectionStatus = this.priceStream.connectionStatus;

  readonly isSubmitting = signal(false);
  readonly submitError = signal<string | null>(null);

  readonly selectedHistory = signal<PriceRecord[]>([]);
  readonly historyLoading = signal(false);

  ngOnInit(): void {
    this.priceStream.connect();
  }

  ngOnDestroy(): void {
    this.priceStream.disconnect();
  }

  submitCheck(): void {
    if (this.urlControl.invalid) {
      this.urlControl.markAsTouched();
      return;
    }
    this.isSubmitting.set(true);
    this.submitError.set(null);

    this.priceStream.triggerCheck(this.urlControl.value).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.urlControl.reset('');
      },
      error: (err) => {
        this.isSubmitting.set(false);
        this.submitError.set(err?.error?.detail ?? 'Failed to queue price check. Please try again.');
      },
    });
  }

  viewHistory(row: PriceCheckRow): void {
    this.historyLoading.set(true);
    this.priceStream.getHistory(row.productUrl).subscribe({
      next: (records) => {
        this.selectedHistory.set(records);
        this.historyLoading.set(false);
      },
      error: () => this.historyLoading.set(false),
    });
  }

  statusBadgeClass(status: PriceCheckRow['status']): string {
    switch (status) {
      case 'completed':
        return 'badge badge-completed';
      case 'failed':
        return 'badge badge-failed';
      case 'in_progress':
        return 'badge badge-progress';
      default:
        return 'badge badge-pending';
    }
  }

  trackByRequestId(_index: number, row: PriceCheckRow): string {
    return row.requestId;
  }
}
