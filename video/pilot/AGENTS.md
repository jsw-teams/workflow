# Codex video QA instructions (copy into the video workflow working directory)

You are the reviewer, not the storyteller. Follow this pipeline in order:

1. Read `shot_contract.json`, `PROMPTS.md`, `REFERENCE_POLICY.md` and `CODEX_QA_STANDARD.md`.
2. Confirm scene master and reference identities, including their SHA-256 values. Never update the locked scene master.
3. Run `python qa_media.py --video <generated_clip> --contract shot_contract.json --out <review_out>`.
4. Check extracted contact sheet and, when necessary, decode additional full-resolution frames. Check actual generated footage against the required state graph. Explicitly verify causal object contact, occlusion direction, support surfaces, object number and scene geography. Do not infer unseen transitions.
5. Record each criterion as PASS, FAIL, or UNVERIFIED with visible evidence. A successful `ffprobe` is only a media check, never a semantic PASS.
6. Mark the exact **observed** narrative completion point if it exists. This is an editing observation after generation, not a preassigned script time. Do not keep redundant footage to match model output length. If intentional reaction/atmosphere continues, record its purpose before retaining it.
7. For failures: restore last approved state + locked scene master; provide the smallest correction to prompts or shot layout, keeping evidence and rejected files. Avoid repeatedly amplifying negative prompts for the same bad output.
8. Never substitute an infographic, style guide, montage, or synthesized still image for a real generated film frame. If the generation path did not actually bind a reference image, report UNVERIFIED rather than treating it as a model-reference failure.
9. Final decision: REJECT on any P0 failure, NEEDS_REVIEW on unverified required criteria, and APPROVE only after all required criteria are explicitly verified.

Important: This package is a reference/test plan, not a claim that Veo or Seedance has been run.
