# Policy 0.2.0 loss analysis (regression sets, read after the run)

Selector blob 22336f88 at 32431e6d. Every number below was computed from the archived rows of the 0.2.0 runs; this analysis motivated policy 0.3.0 and is therefore *fitting* evidence, not qualification.

## LongMemEval_S session plane (full 500)

- questions losing required evidence vs default: 31; lost gold items: 38; by reason: {'subject_mismatch': 11, 'no_query_term_evidence': 27}
- sentences per lost item: min 10, median 16.0, max 25; lost items that are first-person text: {True: 38}
- all omissions by (reason, single_sentence): {('no_query_term_evidence', False): 13198, ('no_query_term_evidence', True): 880, ('subject_mismatch', False): 309, ('subject_mismatch', True): 6, ('attribute_unevidenced', False): 10, ('attribute_unevidenced', True): 1}  -> single-sentence omissions never lost gold
- lost question ids: ['06878be2', '06f04340', '08f4fc43', '09d032c9', '157a136e', '1a8a66a6', '25e5aa4f', '2a1811e2', '58ef2f1c', '61f8c8f8', '6d550036', '8c18457d', '8e91e7d9', '9a707b81', 'a1cc6108', 'ba358f49', 'bc149d6b', 'c18a7dc8', 'd682f1a2', 'gpt4_15e38248', 'gpt4_194be4b3', 'gpt4_31ff4165', 'gpt4_372c3eed', 'gpt4_4929293b', 'gpt4_68e94288', 'gpt4_8279ba03', 'gpt4_d12ceb0e', 'gpt4_e061b84f', 'gpt4_f2262a51', 'gpt4_f420262d', 'gpt4_f49edff3']

## LongMemEval_S turn plane (partial, 193 questions before the run was stopped)

- questions losing required evidence vs default: 7; lost gold items: 9; by reason: {'subject_mismatch': 2, 'no_query_term_evidence': 7}
- sentences per lost item: min 2, median 3, max 4; lost items that are first-person text: {True: 9}
- all omissions by (reason, single_sentence): {('no_query_term_evidence', False): 4546, ('no_query_term_evidence', True): 1005, ('subject_mismatch', True): 15, ('subject_mismatch', False): 66, ('attribute_unevidenced', True): 1, ('attribute_unevidenced', False): 11}  -> single-sentence omissions never lost gold
- lost question ids: ['06878be2', '07b6f563', '58ef2f1c', '6d550036', 'gpt4_194be4b3', 'gpt4_372c3eed', 'gpt4_d12ceb0e']

## LoCoMo (first exposure at 0.2.0; became regression evidence once read)

- conv-26_q4 (single-hop): "What is Caroline's identity?" lost conv-26_session_1 (30 sentences) reason=attribute_unevidenced
- conv-26_q7 (single-hop): "What is Caroline's relationship status?" lost conv-26_session_2 (36 sentences) reason=attribute_unevidenced
- conv-26_q50 (multi-hop): "What would Caroline's political leaning likely be?" lost conv-26_session_12 (49 sentences) reason=attribute_unevidenced
- conv-30_q9 (single-hop): "Which city have both Jean and John visited?" lost conv-30_session_15 (32 sentences) reason=no_query_term_evidence
- conv-41_q40 (single-hop): "What are the names of John's children?" lost conv-41_session_22 (41 sentences) reason=attribute_unevidenced
- conv-42_q5 (single-hop): "What are Joanna's hobbies?" lost conv-42_session_2 (51 sentences) reason=attribute_unevidenced
- conv-43_q28 (multi-hop): "Which popular music composer's tunes does Tim enjoy playing on the piano?" lost conv-43_session_8 (83 sentences) reason=subject_mismatch
- conv-47_q0 (multi-hop): "What are John's suspected health problems?" lost conv-47_session_1 (62 sentences) reason=attribute_unevidenced
- conv-49_q39 (temporal): "How many months lapsed between Sam's first and second doctor's appointment?" lost conv-49_session_2 (39 sentences) reason=attribute_unevidenced

All nine lost LoCoMo documents are whole sessions of 30 to 83 sentences; seven were declined by attribute_unevidenced (the subject is named, the asked attribute is expressed in other words), one by a lowercase possessive anchor ("composer's") and one by term absence.

## Memory-size comparison (sentences / words)

| set | n | sentences min / median / max | words min / median / max |
|---|---:|---|---|
| AMB PrecisionMemBench beliefs | 35 | 1 / 2 / 3 | 5 / 12 / 19 |
| LongMemEval turn plane: gold turns lost at 0.2.0 | 9 | 2 / 3 / 4 | 21 / 58 / 90 |
| LongMemEval session plane: gold sessions lost at 0.2.0 | 38 | 10 / 16.0 / 25 | 158 / 265.0 / 461 |
| LoCoMo: gold sessions lost at 0.2.0 | 9 | 30 / 41 / 83 | 411 / 629 / 1342 |

The lost turn-plane items (2 to 4 sentences, 21 to 90 words) overlap the size class of AMB beliefs (1 to 3 sentences, 5 to 19 words). No sentence-count regime above one sentence, and no word-count regime that is not fitted to these very numbers, separates them. Policy 0.3.0 therefore grounds absence only for single-statement facts and reports uncertainty for everything longer, which forgoes the AMB gain of 0.2.0 (30/77 strict) rather than keep it at the cost of required LongMemEval evidence.
