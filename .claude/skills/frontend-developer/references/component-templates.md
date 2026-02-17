# Component Templates

## Single HTML File Template (Tailwind + Alpine.js + Chart.js)

```html
<!DOCTYPE html>
<html lang="ko" x-data="app()" x-init="init()">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            primary: { DEFAULT: '#6366f1', dark: '#4f46e5' },
            surface: { light: '#ffffff', dark: '#1e1e1e' },
          }
        }
      }
    }
  </script>
  <style>
    [x-cloak] { display: none !important; }
  </style>
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 min-h-screen">

  <!-- Header -->
  <header class="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
      <h1 class="text-xl font-bold">Dashboard</h1>
      <button @click="darkMode = !darkMode" class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
        <span x-show="!darkMode">🌙</span>
        <span x-show="darkMode">☀️</span>
      </button>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 py-8">

    <!-- Summary Cards -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <template x-for="card in summaryCards" :key="card.label">
        <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <p class="text-sm text-gray-500 dark:text-gray-400" x-text="card.label"></p>
          <p class="text-2xl font-bold mt-1" x-text="card.value"></p>
        </div>
      </template>
    </section>

    <!-- Charts Row -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-semibold mb-4">Chart 1</h2>
        <canvas id="chart1"></canvas>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-semibold mb-4">Chart 2</h2>
        <canvas id="chart2"></canvas>
      </div>
    </section>

    <!-- Data Table -->
    <section class="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <h2 class="text-lg font-semibold">Data Table</h2>
        <div class="flex gap-2">
          <template x-for="filter in filters" :key="filter.value">
            <button
              @click="activeFilter = filter.value"
              :class="activeFilter === filter.value
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
              class="px-3 py-1 rounded-full text-sm font-medium transition-colors"
              x-text="filter.label">
            </button>
          </template>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <template x-for="col in columns" :key="col.key">
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                    x-text="col.label"></th>
              </template>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <template x-for="(row, index) in filteredData" :key="row.id">
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                <td class="px-6 py-4 text-sm" x-text="index + 1"></td>
                <!-- Add more columns as needed -->
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div x-show="filteredData.length === 0" class="p-12 text-center text-gray-500">
        <p>데이터가 없습니다.</p>
      </div>
    </section>

  </main>

  <script>
    function app() {
      return {
        darkMode: window.matchMedia('(prefers-color-scheme: dark)').matches,
        activeFilter: 'all',
        data: [],
        summaryCards: [],
        columns: [],
        filters: [
          { label: '전체', value: 'all' },
        ],

        get filteredData() {
          if (this.activeFilter === 'all') return this.data;
          return this.data.filter(item => item.type === this.activeFilter);
        },

        init() {
          this.$watch('darkMode', val => {
            document.documentElement.classList.toggle('dark', val);
          });

          // Initialize charts
          this.initCharts();

          // Load data
          this.loadData();
        },

        async loadData() {
          try {
            // Replace with actual API call
            // const response = await fetch('/api/data');
            // this.data = await response.json();

            // Example data
            this.data = [];
            this.updateSummary();
          } catch (error) {
            console.error('Failed to load data:', error);
          }
        },

        updateSummary() {
          this.summaryCards = [
            { label: 'Total', value: this.data.length },
          ];
        },

        initCharts() {
          // Chart 1
          new Chart(document.getElementById('chart1'), {
            type: 'doughnut',
            data: {
              labels: ['A', 'B', 'C'],
              datasets: [{
                data: [30, 50, 20],
                backgroundColor: ['#22c55e', '#ef4444', '#94a3b8'],
              }]
            },
            options: {
              responsive: true,
              plugins: { legend: { position: 'bottom' } }
            }
          });

          // Chart 2
          new Chart(document.getElementById('chart2'), {
            type: 'bar',
            data: {
              labels: ['Item 1', 'Item 2', 'Item 3'],
              datasets: [{
                label: 'Count',
                data: [12, 19, 8],
                backgroundColor: '#6366f1',
              }]
            },
            options: {
              indexAxis: 'y',
              responsive: true,
              plugins: { legend: { display: false } }
            }
          });
        }
      };
    }
  </script>

</body>
</html>
```

## React Component Templates

### Summary Card
```tsx
interface SummaryCardProps {
  label: string;
  value: string | number;
  change?: { value: number; type: 'increase' | 'decrease' };
  icon?: React.ReactNode;
}

function SummaryCard({ label, value, change, icon }: SummaryCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <p className="text-2xl font-bold mt-2">{value}</p>
      {change && (
        <p className={`text-sm mt-1 ${change.type === 'increase' ? 'text-green-500' : 'text-red-500'}`}>
          {change.type === 'increase' ? '↑' : '↓'} {Math.abs(change.value)}%
        </p>
      )}
    </div>
  );
}
```

### Filter Buttons
```tsx
interface FilterButtonsProps<T extends string> {
  filters: { label: string; value: T }[];
  active: T;
  onChange: (value: T) => void;
}

function FilterButtons<T extends string>({ filters, active, onChange }: FilterButtonsProps<T>) {
  return (
    <div className="flex gap-2 flex-wrap">
      {filters.map((filter) => (
        <button
          key={filter.value}
          onClick={() => onChange(filter.value)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            active === filter.value
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}
```

### Sentiment Badge
```tsx
type Sentiment = 'positive' | 'negative' | 'neutral';

function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  const styles: Record<Sentiment, string> = {
    positive: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    negative: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    neutral: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  };

  const labels: Record<Sentiment, string> = {
    positive: '긍정',
    negative: '부정',
    neutral: '중립',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[sentiment]}`}>
      {labels[sentiment]}
    </span>
  );
}
```

### Star Rating
```tsx
function StarRating({ score, max = 5 }: { score: number; max?: number }) {
  return (
    <div className="flex gap-0.5" aria-label={`${score} out of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => (
        <svg
          key={i}
          className={`w-4 h-4 ${i < score ? 'text-yellow-400' : 'text-gray-300 dark:text-gray-600'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}
```

### Data Import Modal
```tsx
function DataImportModal({ isOpen, onClose, onImport }: {
  isOpen: boolean;
  onClose: () => void;
  onImport: (data: unknown[]) => void;
}) {
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleImport = () => {
    try {
      const parsed = JSON.parse(input);
      if (!Array.isArray(parsed)) {
        throw new Error('JSON 배열 형식이어야 합니다.');
      }
      onImport(parsed);
      onClose();
      setInput('');
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'JSON 파싱에 실패했습니다.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h2 className="text-lg font-semibold">데이터 가져오기</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div className="p-6 flex-1 overflow-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='JSON 배열을 붙여넣으세요...\n예: [{"id": 1, "text": "..."}]'
            className="w-full h-64 p-4 border rounded-lg font-mono text-sm resize-none
                       bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700
                       focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
        </div>
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 dark:text-gray-400">
            취소
          </button>
          <button
            onClick={handleImport}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            가져오기
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Loading Skeleton
```tsx
function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`} />
  );
}

function CardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
      <Skeleton className="h-4 w-24 mb-2" />
      <Skeleton className="h-8 w-16" />
    </div>
  );
}

function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
```
