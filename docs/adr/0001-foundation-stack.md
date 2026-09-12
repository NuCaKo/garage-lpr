# ADR-0001: Foundation teknoloji yığını

- Durum: Kabul edildi
- Tarih: 2026-09-10

## Karar

- Python 3.11+ ve FastAPI: AI ekosistemiyle doğal uyum, typed API ve düşük
  operasyonel karmaşıklık.
- SQLAlchemy 2 + Alembic + SQLite: repository sınırı, migration disiplini ve tek
  PC'de harici database servisi gerektirmeyen kalıcılık.
- Pydantic Settings: environment bootstrap değerlerinin tek yerde doğrulanması.
- React + TypeScript + Vite: server-side rendering ihtiyacı olmayan yerel UI için
  Next.js'ten daha küçük runtime yüzeyi.
- ONNX Runtime ve OpenCV Phase 3'e ertelenir: Phase 1 kurulumuna büyük native
  paketler ve kullanılmayan kaynak tüketimi eklenmez.
- Native Windows deployment birinci sınıftır; Docker opsiyonel kalır.

## Sonuçlar

Backend ve frontend ayrı build edilir ancak production paketlemede FastAPI,
frontend'in statik çıktısını sunabilir. Donanım adaptörleri Python process'i
içinde başlar; çökme izolasyonu ve ayrı worker process kararı ölçüm sonuçlarına
göre sonraki fazlarda verilir.
