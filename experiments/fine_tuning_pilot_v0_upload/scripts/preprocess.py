"""Qwen chat-template preprocessing with assistant-completion-only supervision."""
IGNORE_INDEX = -100

def build_feature(tokenizer, messages, max_length):
    """Return an SFT feature that retains completion tokens before truncating context."""
    prompt_messages = [m for m in messages if m['role'] != 'assistant']
    prefix_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
    full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prefix_ids = tokenizer(prefix_text, add_special_tokens=False)['input_ids']
    full_ids = tokenizer(full_text, add_special_tokens=False)['input_ids']
    if full_ids[:len(prefix_ids)] != prefix_ids:
        raise ValueError('CHAT_TEMPLATE_PREFIX_MISMATCH')
    answer_ids = full_ids[len(prefix_ids):]
    if not answer_ids:
        raise ValueError('EMPTY_ASSISTANT_COMPLETION')
    answer_truncated = len(answer_ids) > max_length
    if answer_truncated:
        kept_answer = answer_ids[:max_length]
        kept_prompt = []
    else:
        kept_answer = answer_ids
        kept_prompt = prefix_ids[-(max_length-len(kept_answer)):]
    input_ids = kept_prompt + kept_answer
    labels = [IGNORE_INDEX] * len(kept_prompt) + kept_answer
    return {
        'input_ids': input_ids,
        'attention_mask': [1] * len(input_ids),
        'labels': labels,
        'full_length': len(full_ids),
        'prompt_length': len(prefix_ids),
        'answer_length': len(answer_ids),
        'context_truncated': len(prefix_ids) + len(answer_ids) > max_length and not answer_truncated,
        'answer_truncated': answer_truncated,
        'supervised_tokens': len(kept_answer),
    }
