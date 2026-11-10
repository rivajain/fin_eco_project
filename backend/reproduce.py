"""Standalone reproduction script; prints the same summary metrics as backend."""
import argparse, json
from pathlib import Path
import pandas as pd
from evaluation import rolling_evaluation

def main():
    p=argparse.ArgumentParser(description="Reproduce Horserace out-of-sample evaluation.")
    p.add_argument("--csv",required=True,help="CSV with date, returns, exog_1, exog_2, ...")
    p.add_argument("--window",type=int,default=500)
    p.add_argument("--evaluation-size",type=int,default=250)
    p.add_argument("--horizon",type=int,default=1)
    p.add_argument("--scheme",choices=["rolling","expanding"],default="expanding")
    p.add_argument("--arima-order",type=int,nargs=3,default=[1,0,1])
    p.add_argument("--output",default=None,help="Optional JSON output path")
    a=p.parse_args()
    df=pd.read_csv(a.csv)
    cols=sorted([c for c in df.columns if c.startswith("exog_")])
    if "returns" not in df or len(cols)<2:
        raise SystemExit("CSV must include returns and >=2 exog_* columns.")
    result=rolling_evaluation(df.returns.to_numpy(),df[cols].to_numpy(),
        window=a.window,evaluation_size=a.evaluation_size,horizon=a.horizon,
        scheme=a.scheme,arima_order=tuple(a.arima_order))
    result["data_file"]=str(Path(a.csv))
    out=json.dumps(result,indent=2)
    if a.output: Path(a.output).write_text(out)
    print(out)
if __name__=="__main__": main()
