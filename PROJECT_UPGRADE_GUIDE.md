# TestPilot Lite RAG Upgrade Guide

Bu dosya, projenin Microsoft sertifika seviyesi için nasıl güçlendirileceğini ve hangi adımların öncelikli olduğunu açıklar. Proje üzerinde çalışırken buraya bakabilir, eklenen özellikleri ve hedefleri takip edebilirsin.

---

## 1. Projenin mevcut seviyesi

Şu anda proje, aşağıdakileri içeren ciddi bir MVP seviyesine ulaşmış durumda:

- FastAPI backend
- SQLite + SQLAlchemy metadata tabanı
- Document ve Chunk tabloları
- Metin/dosya yükleme endpointleri
- Chunking servisi
- Embedding servisi
- ChromaDB / fallback vector store
- RAG retrieval servisi
- Test generation endpoint
- JSON / Markdown / CSV / Gherkin çıktı desteği
- Evaluation service
- React frontend
- Dashboard, Documents, Generate Tests, Results, History sayfaları
- Dark modern UI
- Export butonları
- localStorage history

Bu, tek başına şöyle bir iddia koyuyor:

> “Ben RAG pipeline’ının ana parçalarını biliyorum: document ingestion, chunking, embedding, vector search, retrieval, structured generation, export ve evaluation.”

Ancak projeyi Microsoft sertifika düzeyine taşıyacak asıl fark şu:

> Test üretimi artık sadece template/deterministic olmamalı. Gerçek bir LLM tabanlı generation sürecine oturmalı.

---

## 2. En kritik eksik: gerçek LLM entegrasyonu

### Hedef

- Template generator → gerçek AI generator
- Gerçek AI çıktısını çekirdeğe sokmak
- Hem bulut hem local sağlayıcıları desteklemek
- Model yoksa mock/fallback ile sistemin çalışmasını sağlamak

### Yapılması gereken

- `services/llm/` mimarisi oluştur
- Provider-independent adapter yapısı kur
- `LLM_PROVIDER` ile seçim yap
- JSON schema tabanlı çıktılar elde et
- Pydantic ile validate et
- Bozuk JSON dönerse tamir / fallback kullan

### Örnek provider listesi

- `mock`
- `openai`
- `azure_openai`
- `ollama`
- `foundry_local` (opsiyonel / ileride)

### .env örneği

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 3. Structured JSON schema zorunluluğu

LLM’den gelen test case’leri sadece düz metin olarak kullanmak yeterli değildir.

### Önerilen model

```json
{
  "title": "Password reset request with invalid email",
  "type": "Negative",
  "priority": "High",
  "preconditions": [
    "User is on the password reset page"
  ],
  "steps": [
    "Enter an invalid email address",
    "Click the reset password button"
  ],
  "expected_result": "System displays an email validation error.",
  "source_references": [
    {
      "document_name": "auth_user_stories.md",
      "chunk_id": "chunk_004",
      "quote": "Invalid email should show an error."
    }
  ],
  "confidence": 0.82
}
```

### Önemli alanlar

- `source_references`
- `confidence`
- `type`
- `priority`
- `expected_result`
- `steps`

### Neden

Bu alanlar olmazsa çıktı sadece “AI yazısı” gibi durur. Bu alanlar olursa proje **test management assistant** olarak görünür.

---

## 4. Requirement Coverage Matrix

Bence projenin en etkileyici yeni özelliği requirement coverage matrix olacak.

### Neden güçlü

- Testlerin requirements ile takip edildiğini gösterir
- Test üretmenin ötesine geçer
- Jüriye “riskleri ve eksiklikleri gördüğünü” gösterir

### Yapılabilecek

- Her requirement veya user story için test sayısı hesapla
- Covered / uncovered requirement göster
- “Generate missing tests” butonu ekle

### Bir örnek tablo

| Requirement | Positive | Negative | Edge | Security | Total | Coverage |
|-------------|----------|----------|------|----------|-------|----------|
| Login with valid credentials | 1 | 1 | 1 | 1 | 4 | 100% |
| Password reset token expires | 1 | 2 | 1 | 0 | 4 | 75% |

---

## 5. OpenAPI / API Test Mode

OpenAPI desteği bu projeyi çok daha sofistike yapar.

### Yapılması gereken

- OpenAPI / Swagger dosyası yükleme desteği
- Endpointleri parse etme
- API test case’leri üretme
- Status code, payload, body validation testleri ekleme

### Bu ne sağlar?

- Projeyi sadece doküman testinden API testine genişletir
- Bunu Microsoft sertifika sunumunda kolaylıkla anlatabilirsin
- “API test planning assistant” mesajını güçlendirir

---

## 6. Playwright / Cypress skeleton export

Gerçek çalışan test otomasyonu gerekmez.

### Yapılabilecek en güvenli yaklaşım

- LLM’den sadece skeleton kod iste
- `placeholder selector` kullan
- Kullanıcıya not göster: “Selectors may require adjustment”

### Bu neden iyi?

- Proje “test otomasyonu”na yakın olur
- Ancak gerçek çalışma garantisi zorlamaz
- Sunumda ciddi bir feature olarak gösterilir

---

## 7. Backend history’in database’e taşınması

Şu an history localStorage’da. Demo için yeter ama ciddi proje için zayıf.

### Yapılması gereken

- `GenerationRun` modeli
- `GeneratedTestCase` modeli
- `EvaluationResult` modeli
- History sayfasını backend’den çek

### Bu ne kazandırır?

- Geçmiş jenerasyonları tekrar açma
- Aynı feature için önceki sonuçları görme
- Export’u tekrar alma
- Dashboard metriklerini gerçek veriden üretme

---

## 8. Project / Workspace desteği

Proje bazlı doküman ve retrieval kesinlikle olmalı.

### Neden?

- Tek havuzda farklı projeler karışabilir
- UI’da proje seçimi ciddi durur
- Retrieval sadece seçili proje için yapılmalı

### Öneri

- `Project` varlığı ekle
- Document ve Chunk’ları project-scoped yap
- Frontend’de proje seçimi

---

## 9. RAG tarafını güçlendirme

Şu an chunking + embedding + Chroma var. Güzel. Ancak daha profesyonel RAG için: 

### 9.1 Heading-aware chunking

- Markdown başlıklarına göre chunk
- OpenAPI endpointlerine göre chunk
- User story / acceptance criteria bazlı chunk

### 9.2 Hybrid search

- Vector search + keyword match
- Top 10 aldıktan sonra rerank

### 9.3 Retrieved context preview

- Kullanıcıya hangi chunk’lar kullanıldı göster
- Source references paneli ekle

### 9.4 Insufficient context handling

- Yeterli bağlam yoksa test uydurma
- Kullanıcıya doğru şekilde bildir

---

## 10. Evaluation service’i geliştir

Daha ciddi bir evaluation modülü olmalı.

### Önerilen skorlar

- Completion score
- Groundedness score
- Coverage score
- Duplicate score
- Risk score

### Neden?

Microsoft Foundry docs’unda evaluation, RAG’ın önemli bileşeni olarak geçiyor. Bu skorlar projeyi “uygulamalı kalite kontrol” seviyesine taşır.

---

## 11. Generate missing tests

Eksik test türlerini tespit etmek ve yeniden üretmek çok güçlü.

### Workflow

- İlk generation
- Quality evaluation
- Missing categories bildir
- “Generate missing tests” butonu

---

## 12. Human review / status metası

AI tarafından üretilen testler doğrudan kabul edilmemeli.

### Yapılabilecek

- Draft / Reviewed / Approved / Rejected / Needs Revision
- Her test case için not ekleme
- Kullanıcı arayüzünde review workflow

---

## 13. Prompt template yönetimi

Prompt’ları kod içinde sabitlemek yerine dosyaya taşı.

### Önerilen yapı

- `prompts/test_case_generation.md`
- `prompts/gherkin_generation.md`
- `prompts/api_test_generation.md`
- `prompts/evaluation.md`

### Advanced ayar

- Test style seçimi
- Security focused
- BDD focused
- API testing

---

## 14. API uç noktası mimarisi

Mevcut endpointler güzeldir ama daha ürün gibi görünmesi için:

- `POST /api/projects`
- `POST /api/projects/{project_id}/documents/upload-text`
- `POST /api/projects/{project_id}/generate-tests`
- `GET /api/generation-runs`
- `POST /api/test-cases/{id}/regenerate`

---

## 15. Frontend sayfa önerileri

Mevcut sayfalar iyi. Ek olarak:

- Project Selector
- Coverage Matrix
- Test Case Library
- Retrieved Context Panel
- Evaluation Details

---

## 16. Export geliştirme

Mevcut export iyi. Ek olarak:

- Excel export
- Postman collection export
- Jira/Azure DevOps CSV uyumluluğu
- Markdown summary report

---

## 17. Demo dataset

En iyi demo dataset çok değerli.

Öneri:

1. Authentication demo
2. E-commerce checkout demo
3. Course management demo

Authentication demo en güçlüsü.

---

## 18. README ve dokümantasyon

Proje README’si ürün dokümanı gibi olmalı.

### İçerik

- Problem
- Çözüm
- Key features
- Architecture
- Tech stack
- Demo senaryosu
- Future work

---

## 19. Microsoft sertifika sunumu için ifadeler

Kullanılabilecek güçlü cümleler:

- “TestPilot Lite RAG is not a generic chatbot. It is a document-grounded software testing assistant.”
- “The system retrieves relevant project context before generating each test case.”
- “Each generated test case includes source references, priority, steps, expected results, and exportable formats.”
- “The architecture is provider-independent for OpenAI, Azure OpenAI, Ollama, or Foundry Local.”

---

## 20. Eklenmemesi gerekenler

Şimdilik kaçın:

- Tam authentication/rol yönetimi
- Tam multi-tenant SaaS mimarisi
- Gerçek Jira entegrasyonu
- Full çalışan Playwright otomasyonu
- Komple agent sistemi

---

## 21. Öncelik sırası

### Aşama 1 — Gerçek AI projeye dönüştür

1. LLM provider adapter
2. Mock provider fallback
3. JSON schema validation
4. Prompt template yönetimi

### Aşama 2 — Backend ürünleştir

1. Backend history DB
2. GeneratedTestCase modeli
3. EvaluationResult modeli
4. Project/workspace mantığı

### Aşama 3 — Test domainini güçlendir

1. Requirement extraction
2. Coverage matrix
3. API/OpenAPI mode
4. Test case review status

### Aşama 4 — Demo ve export

1. Excel/Markdown report
2. Gherkin/export iyileştirme
3. Playwright skeleton
4. Demo docs

### Aşama 5 — Kalite

1. README
2. Architecture diagram
3. Demo script
4. Screenshots
5. Unit tests
6. Docker compose

---

## 22. En yüksek değerli özellikler

Zaman azsa sadece bunları yap:

1. Gerçek LLM provider adapter
2. Source-grounded structured output
3. Backend-persisted generation history
4. Coverage matrix
5. OpenAPI/API test mode

---

## 23. Kod mimarisi önerisi

### Backend önerilen yapı

```
backend/app/
  api/
  db/
  llm/
  schemas/
  services/
  prompts/
  utils/
```

### Frontend önerilen yapı

```
frontend/src/
  api/
  components/
  pages/
  types/
```

---

## 24. Demo akış önerisi

1. Problem tanımı
2. Mimari gösterimi
3. Doküman yükleme
4. Generate Tests demo
5. Source references + evaluation gösterimi
6. Export gösterimi
7. Future work

---

## 25. Stage 1: Yapılacak ilk iş

1. `backend/app/llm/` dizinini oluştur
2. Provider-independent adapter ekle
3. Mock provider’ı koru
4. `schemas/` ile JSON output ’ı doğrula
5. `generation_service.py` gerçek provider kullanır hale getir
6. `generation` API endpoint’i schema ile yanıt döner

---

## 26. Bu dosyayı referans olarak kullan

Proje üzerinde çalışırken bu dosyayı sürekli rehber olarak kullan. Her kod değişikliğini buradaki önceliklere göre yap.
