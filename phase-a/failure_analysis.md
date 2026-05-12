# PhÃ¢n TÃ­ch Lá»—i

## 10 cÃ¢u há»i tá»‡ nháº¥t

| rank | evolution_type | avg_score | faithfulness | answer_relevancy | context_precision | context_recall | question |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | reasoning | 0.3703 | 1.0000 | 0.0000 | 0.0720 | 0.4091 | Theo Äiá»u 112, trong trÆ°á»ng há»£p nÃ o nghá»‰ Ä‘Æ°á»£c Ã¡p dá»¥ng? |
| 2 | simple | 0.3988 | 1.0000 | 0.0000 | 0.1408 | 0.4545 | Theo Äiá»u 1, ná»™i dung quy Ä‘á»‹nh vá» pháº¡m vi Ä‘iá»u chá»‰nh lÃ  gÃ¬? |
| 3 | reasoning | 0.4009 | 1.0000 | 0.1064 | 0.0526 | 0.4444 | Theo Äiá»u 185, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» há»™i lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |
| 4 | multi_context | 0.404 | 1.0000 | 0.0000 | 0.1714 | 0.4444 | Äiá»u 1 (Pháº¡m vi Ä‘iá»u chá»‰nh) vÃ  Äiá»u 2 (Äá»‘i tÆ°á»£ng Ã¡p dá»¥ng) cÃ¹ng lÃ m rÃµ ná»™i dung gÃ¬ trong chÆ°Æ¡ng nÃ y? |
| 5 | reasoning | 0.4045 | 1.0000 | 0.1818 | 0.0364 | 0.4000 | Theo Äiá»u 54, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» doanh lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |
| 6 | multi_context | 0.4077 | 1.0000 | 0.0000 | 0.0890 | 0.5417 | Äiá»u 2 (Äá»‘i tÆ°á»£ng Ã¡p dá»¥ng) vÃ  Äiá»u 3 (Giáº£i thÃ­ch tá»« ngá»¯) cÃ¹ng lÃ m rÃµ ná»™i dung gÃ¬ trong chÆ°Æ¡ng nÃ y? |
| 7 | reasoning | 0.4365 | 1.0000 | 0.1429 | 0.0696 | 0.5333 | Theo Äiá»u 55, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» há»£p lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |
| 8 | reasoning | 0.505 | 1.0000 | 0.2857 | 0.1343 | 0.6000 | Theo Äiá»u 35, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» quyá»n lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |
| 9 | reasoning | 0.5064 | 1.0000 | 0.0000 | 0.0921 | 0.9333 | Theo Äiá»u 169, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» tuá»•i lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |
| 10 | reasoning | 0.5124 | 1.0000 | 0.7500 | 0.0737 | 0.2258 | Theo Äiá»u 113, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» nghá»‰ lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? |

## CÃ¡c Cluster ÄÃ£ XÃ¡c Äá»‹nh

### Cluster C1: Lá»—i parsing Ä‘iá»u kiá»‡n / single-hop reasoning

**Root cause:** Lá»—i parsing Ä‘iá»u kiá»‡n / single-hop reasoning.
**Proposed fix:** Viáº¿t láº¡i cÃ¢u há»i sao cho mÃ´ hÃ¬nh cÃ³ má»™t Ä‘iá»u kiá»‡n phÃ¡p lÃ½ rÃµ rÃ ng Ä‘á»ƒ trÃ­ch xuáº¥t, hoáº·c bá»• sung má»™t bá»™ truy xuáº¥t chuyÃªn biá»‡t dÃ nh cho cÃ¡c má»‡nh Ä‘á» chá»©a sá»‘ liá»‡u vÃ  Ä‘iá»u kiá»‡n.

**VÃ­ dá»¥:**
- [reasoning] Theo Äiá»u 112, trong trÆ°á»ng há»£p nÃ o nghá»‰ Ä‘Æ°á»£c Ã¡p dá»¥ng? | avg=0.3703 | worst=answer_relevancy
- [reasoning] Theo Äiá»u 185, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» há»™i lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? | avg=0.4009 | worst=context_precision
- [reasoning] Theo Äiá»u 54, quy Ä‘á»‹nh cá»¥ thá»ƒ vá» doanh lÃ  bao nhiÃªu hoáº·c nhÆ° tháº¿ nÃ o? | avg=0.4045 | worst=context_precision

### Cluster C2: Retriever bá» sÃ³t ngá»¯ cáº£nh chÃ­nh

**Root cause:** Retriever bá» sÃ³t ngá»¯ cáº£nh chÃ­nh.
**Proposed fix:** Cáº£i thiá»‡n chunking hoáº·c tÄƒng top-k trÆ°á»›c khi generation; kiá»ƒm tra xem báº±ng chá»©ng cÃ³ bá»‹ tÃ¡ch sang nhiá»u chunk hay khÃ´ng.

**VÃ­ dá»¥:**
- [simple] Theo Äiá»u 1, ná»™i dung quy Ä‘á»‹nh vá» pháº¡m vi Ä‘iá»u chá»‰nh lÃ  gÃ¬? | avg=0.3988 | worst=answer_relevancy

### Cluster C3: Lá»—i multi-hop reasoning

**Root cause:** Lá»—i multi-hop reasoning.
**Proposed fix:** Truy xuáº¥t nhiá»u hÆ¡n má»™t Ä‘oáº¡n há»— trá»£ vÃ  yÃªu cáº§u mÃ´ hÃ¬nh káº¿t há»£p chÃºng trÆ°á»›c khi Ä‘Æ°a ra cÃ¢u tráº£ lá»i.

**VÃ­ dá»¥:**
- [multi_context] Äiá»u 1 (Pháº¡m vi Ä‘iá»u chá»‰nh) vÃ  Äiá»u 2 (Äá»‘i tÆ°á»£ng Ã¡p dá»¥ng) cÃ¹ng lÃ m rÃµ ná»™i dung gÃ¬ trong chÆ°Æ¡ng nÃ y? | avg=0.404 | worst=answer_relevancy
- [multi_context] Äiá»u 2 (Äá»‘i tÆ°á»£ng Ã¡p dá»¥ng) vÃ  Äiá»u 3 (Giáº£i thÃ­ch tá»« ngá»¯) cÃ¹ng lÃ m rÃµ ná»™i dung gÃ¬ trong chÆ°Æ¡ng nÃ y? | avg=0.4077 | worst=answer_relevancy

## Acceptance Criteria Check

- Reviewed bottom 10 questions
- Identified 3 clusters
- Each cluster has at least one concrete fix
- The worst questions are dominated by multi-context and reasoning failures, which matches the current evaluator behavior and highlights retrieval/reasoning risks.

