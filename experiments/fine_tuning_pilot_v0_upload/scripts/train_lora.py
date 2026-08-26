"""GPU-only Pilot V0 LoRA entry point; never invoked by package preparation."""
import argparse, datetime, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',default='config/training_config.yaml'); p.add_argument('--resume_from_checkpoint',default=None); a=p.parse_args()
    import torch, yaml
    if not torch.cuda.is_available(): raise SystemExit('CUDA_REQUIRED_TRAINING_STOPPED')
    cfg=yaml.safe_load(Path(a.config).read_text(encoding='utf-8'))
    if cfg['bf16'] and not torch.cuda.is_bf16_supported(): raise SystemExit('BF16_REQUIRED_BUT_UNSUPPORTED')
    if cfg['fp16'] and cfg['bf16']: raise SystemExit('INVALID_MIXED_PRECISION_CONFIG')
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainerCallback, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import DataLoader
    from preprocess import build_feature
    from family_sampler import EpochAwareFamilySampler
    root=Path(__file__).resolve().parents[1]
    run_id=f"{cfg['run_name_prefix']}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_seed{cfg['seed']}"
    out=root/cfg['output_dir']/run_id; out.mkdir(parents=True,exist_ok=False)
    tok=AutoTokenizer.from_pretrained(root/'scripts/qwen_tokenizer',local_files_only=True); tok.pad_token=tok.pad_token or tok.eos_token
    def load(name):
        rows=[json.loads(x) for x in (root/'data'/name).read_text(encoding='utf-8').splitlines() if x.strip()]
        return [build_feature(tok,x['messages'],int(cfg['max_seq_length'])) for x in rows], [x['metadata']['task_family'] for x in rows]
    train,families=load('train.jsonl'); val,_=load('validation.jsonl')
    sampler=EpochAwareFamilySampler(families,seed=cfg['seed'],mathematical_reasoning_ratio=cfg['sampling']['mathematical_reasoning_target_ratio'],num_samples=cfg['sampling']['epoch_sample_count'])
    class Collator:
        def __call__(self,items):
            n=max(len(x['input_ids']) for x in items); pad=tok.pad_token_id
            return {'input_ids':torch.tensor([x['input_ids']+[pad]*(n-len(x['input_ids'])) for x in items]),'attention_mask':torch.tensor([x['attention_mask']+[0]*(n-len(x['attention_mask'])) for x in items]),'labels':torch.tensor([x['labels']+[-100]*(n-len(x['labels'])) for x in items])}
    class FamilyTrainer(Trainer):
        def get_train_dataloader(self):
            return DataLoader(self.train_dataset,batch_size=self._train_batch_size,sampler=sampler,collate_fn=self.data_collator,drop_last=False)
    class SamplingCallback(TrainerCallback):
        def on_epoch_begin(self,args,state,control,**kwargs): sampler.set_epoch(int(state.epoch or 0))
        def on_epoch_end(self,args,state,control,**kwargs): (out/'effective_sampling_statistics.json').write_text(json.dumps({'epochs':sampler.history},ensure_ascii=False,indent=2),encoding='utf-8')
    model=AutoModelForCausalLM.from_pretrained(cfg['base_model'],torch_dtype=torch.bfloat16)
    lora=cfg['lora']; model=get_peft_model(model,LoraConfig(r=lora['r'],lora_alpha=lora['alpha'],lora_dropout=lora['dropout'],target_modules=lora['target_modules'],task_type='CAUSAL_LM'))
    args=TrainingArguments(output_dir=str(out),num_train_epochs=cfg['epochs'],learning_rate=cfg['learning_rate'],per_device_train_batch_size=cfg['per_device_train_batch_size'],per_device_eval_batch_size=cfg['per_device_train_batch_size'],gradient_accumulation_steps=cfg['gradient_accumulation_steps'],evaluation_strategy='steps',save_strategy='steps',logging_steps=cfg['logging_steps'],save_steps=cfg['save_steps'],eval_steps=cfg['eval_steps'],save_total_limit=cfg['save_total_limit'],gradient_checkpointing=cfg['gradient_checkpointing'],bf16=cfg['bf16'],fp16=cfg['fp16'],seed=cfg['seed'],report_to='none',remove_unused_columns=False)
    trainer=FamilyTrainer(model=model,args=args,train_dataset=train,eval_dataset=val,data_collator=Collator(),callbacks=[SamplingCallback()])
    trainer.train(resume_from_checkpoint=a.resume_from_checkpoint); metrics=trainer.evaluate(); model.save_pretrained(out); tok.save_pretrained(out)
    (out/'training_config_snapshot.yaml').write_text(Path(a.config).read_text(encoding='utf-8'),encoding='utf-8')
    (out/'run_manifest.json').write_text(json.dumps({'run_id':run_id,'base_model':cfg['base_model'],'resume_from_checkpoint':a.resume_from_checkpoint,'final_validation':metrics,'adapter_merged':False,'gguf_exported':False},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
