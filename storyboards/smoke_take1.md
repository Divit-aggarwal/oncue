# What is RAG (pipeline test)

Status: APPROVED by creator (2026-09-17).
Audio: `video/public/audio/smoke_take1.mp3` (existing take, 12.05s). Test only: shorter than the 30–60s / 90–120 word target.
Visuals: plain text and boxes, all TEMPORARY. No canonical characters or styles.

**Hook (first 3s):** Basically RAG mein model ko dobara train nahi kar rahe.

## Beat 1

**Say:** Basically RAG mein model ko dobara train nahi kar rahe.

**Screen:** Headline "RAG" fades in at centre. On "dobara train", a smaller line appears below: "no retraining". The model's weights stay unchanged.

## Beat 2

**Say:** Hum bas model ko notes de rahe hain.

**Screen:** Beat 1 text fades out. A box labelled "LLM" appears. A smaller box labelled "notes" slides in from the left and stops next to it, with a caption below: "extra context in the prompt".

## Beat 3

**Say:** Retriever relevant documents dhoondta hai, aur LLM answer likhta hai.

**Screen:** Beat 2 boxes fade out. A vertical flow builds from the top: "Retriever" box, a line down to "relevant docs". On "LLM answer", a line continues down to an "LLM" box, then to "answer". Holds until the audio ends.

## Technical check

RAG retrieves relevant documents at question time and inserts them into the model's context (the prompt). The model's weights are not changed. "Notes" is a fair simplification: the model reads them for this one answer and does not learn them permanently.
