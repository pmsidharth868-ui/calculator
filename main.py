from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

GRP3_PARAMS = {
    "MNL1": {"rebate_1": 0.0204, "rebate_2": 0.0099, "od_rate": 0.0301, "od_rate_2": 0.0301, "od_inc_days": 270},
    "MNL12": {"rebate_1": 0.0899, "rebate_2": 0.0299, "od_rate": 0.0101, "od_rate_2": 0.0301, "od_inc_days": 365},
    "MNL21": {"rebate_1": 0.0849, "rebate_2": 0.0099, "od_rate": 0.0301, "od_rate_2": 0.0301, "od_inc_days": 365},
    "MPT5":  {"rebate_1": 0.0599, "rebate_2": 0.0099, "od_rate": 0.0101, "od_rate_2": 0.0301, "od_inc_days": 270},
    "MPT10": {"rebate_1": 0.0749, "rebate_2": 0.0199, "od_rate": 0.0101, "od_rate_2": 0.0301, "od_inc_days": 270},
    "MPT20": {"rebate_1": 0.0899, "rebate_2": 0.0299, "od_rate": 0.0101, "od_rate_2": 0.0301, "od_inc_days": 270},
    "MPT30": {"rebate_1": 0.1109, "rebate_2": 0.0399, "od_rate": 0.0101, "od_rate_2": 0.0301, "od_inc_days": 365},
    "MSP01": {"rebate_1": 0.0599, "rebate_2": 0.0299, "od_rate": 0.000099, "od_rate_2": 0.0301, "od_inc_days": 270},
}

GRP4_PARAMS ={
    "MSP02": {"rebate_1": 0.0899, "rebate_2": 0.0499, "rebate_3": 0.0099, "od_rate": 0.0301, "od_inc_days": 270},
    "MSP03": {"rebate_1": 0.0604, "rebate_2": 0.0299, "rebate_3": 0.000099, "od_rate": 0.0301, "od_inc_days": 270},
    "MSP04": {"rebate_1": 0.0904, "rebate_2": 0.0499, "rebate_3": 0.0099, "od_rate": 0.0301, "od_inc_days": 270},
    "MSP05": {"rebate_1": 0.0599, "rebate_2": 0.0299, "rebate_3": 0.000099, "od_rate": 0.0301, "od_inc_days": 270},
    "MSP06": {"rebate_1": 0.0899, "rebate_2": 0.0499, "rebate_3": 0.0099, "od_rate": 0.0301, "od_inc_days": 270},
}

SCHEME_RATES = {k.strip().upper(): {"int_rate": 0.20, "sc_rate": 0.0099} for k in list(GRP3_PARAMS.keys()) + list(GRP4_PARAMS.keys())}

class RowData(BaseModel):
    Date: str
    ad_Charges: float
    Credit: float

class CalculateRequest(BaseModel):
    scheme: str
    pledge_value: float
    pledge_date: str
    input_df: List[RowData]


def calculate_pledge_values(scheme, pledge_value, dates_input, add_charges_input, credits_input):
    scheme = str(scheme).strip().upper()

    if scheme not in SCHEME_RATES:
        return {"error": f"Error: Scheme '{scheme}' is not recognized."}

    try:
        pledge_value = float(pledge_value)
    except (ValueError, TypeError):
        return {"error": "Error: Invalid pledge value."}

    try:
        date_strs = [d.strip() for d in str(dates_input).split(',') if d.strip()]
        dates = [datetime.strptime(d, "%d/%m/%Y") for d in date_strs]
    except ValueError:
        return {"error": "Error: Invalid date format. Use dd/mm/yyyy."}

    if len(dates) < 2:
        return {"error": "Error: Please enter at least one intervals date."}

    try:
        add_charges_input = "0" if not add_charges_input else str(add_charges_input)
        add_charges = [float(d.strip()) for d in add_charges_input.split(',') if d.strip()]
    except ValueError:
        return {"error": "Error: Invalid Additional Charges format."}

    try:
        credits_input = "0" if not credits_input else str(credits_input)
        credits = [float(d.strip()) for d in credits_input.split(',') if d.strip()]
    except ValueError:
        return {"error": "Error: Invalid Credit Amounts format."}

    num_periods = len(dates) - 1
    if len(add_charges) < num_periods:
        add_charges += [0.0] * (num_periods - len(add_charges))
    if len(credits) < num_periods:
        credits += [0.0] * (num_periods - len(credits))

    rates = SCHEME_RATES[scheme]
    int_rate = rates["int_rate"]
    sc_rate = rates["sc_rate"]
    results = []
   
    if scheme in GRP3_PARAMS:
        params = GRP3_PARAMS[scheme]
        re_rate_1 = params["rebate_1"]
        re_rate_2 = params["rebate_2"]
        base_od_rate = params["od_rate"]
        od_rate_2 = params["od_rate_2"]
        od_inc_days = params["od_inc_days"]

        accumulated_int = 0
        accumulated_sc_total = 0
        accumulated_od_total = 0
        accumulated_rebate = 0
        accumulated_add_charges = 0
        accumulated_credits = 0
        cumulative_days_before = 0

        for i in range(len(dates) - 1):
            opening_balance = pledge_value + accumulated_int + accumulated_sc_total + accumulated_od_total + accumulated_add_charges - accumulated_rebate - accumulated_credits
            d1 = dates[i]
            d2 = dates[i+1]
            diff = (d2 - d1).days

            if i == 0:
                diff += 1

            cumulative_days_after = cumulative_days_before + diff
            total_dues = accumulated_int + accumulated_sc_total + accumulated_od_total + accumulated_add_charges - accumulated_rebate
            excess_credit = max(0, accumulated_credits - total_dues)
            unpaid_add_charges = max(0, accumulated_add_charges - accumulated_credits)
            current_principal = max(0.0, pledge_value + unpaid_add_charges - excess_credit)

            total_sc_unrounded = (current_principal * sc_rate * diff) / 360.0
            total_int_unrounded = 0.0
            total_od_unrounded = 0.0
            total_rebate_unrounded = 0.0

            if diff > 60:
                remaining_days = 60
                running_principal = current_principal
                split_index = 0
               
                while remaining_days > 0:
                    days_to_process = min(remaining_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                    
                    applicable_rebate_rate = re_rate_1 if split_index == 0 else re_rate_2
                    split_rebate = (running_principal * applicable_rebate_rate * days_to_process) / 360.0
                    total_rebate_unrounded += split_rebate

                    total_int_unrounded += split_int
                    running_principal += split_int
                    remaining_days -= days_to_process
                    split_index += 1
               
                extra_days = diff - 60
                split_index = 2
               
                while extra_days > 0:
                    days_to_process = min(extra_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                   
                    current_chunk_od_rate = base_od_rate if split_index == 2 else od_rate_2
                    if cumulative_days_after > od_inc_days:
                        current_chunk_od_rate += 0.02

                    split_od = (running_principal * current_chunk_od_rate * days_to_process) / 360.0
                   
                    total_int_unrounded += split_int
                    total_od_unrounded += split_od
                   
                    running_principal += (split_int + split_od)
                    extra_days -= days_to_process
                    split_index += 1

            else:
                remaining_days = diff
                running_principal = current_principal
                
                # FIX: Decide standard rate based on total days instead of progressive slabs
                applicable_rebate_rate = re_rate_1 if diff <= 30 else re_rate_2

                while remaining_days > 0:
                    days_to_process = min(remaining_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                   
                    split_rebate = (running_principal * applicable_rebate_rate * days_to_process) / 360.0

                    total_int_unrounded += split_int
                    total_rebate_unrounded += split_rebate

                    running_principal += split_int
                    remaining_days -= days_to_process

            total_int = round(total_int_unrounded)
            total_sc = round(total_sc_unrounded)
            total_od = round(total_od_unrounded)
            re_val = round(total_rebate_unrounded)
           
            if (d2 - d1).days == 60:
                current_v_od_rate = base_od_rate
                if cumulative_days_after > od_inc_days:
                    current_v_od_rate += 0.02
                V = round((current_principal * re_rate_1 * 30) / 360.0) + round((current_principal * re_rate_2 * 30) / 360.0) + round((current_principal * current_v_od_rate * 1) / 360.0)
                re_val += V
                total_od = 0
                
            if total_od > 0:
                re_val = 0

            accumulated_rebate += re_val

            current_add_charge = add_charges[i]
            current_credit = credits[i]
            if 30 < (d2-d1).days <= 35:
                total_od = 0
                
            closing_balance = opening_balance + total_int + total_sc + total_od + current_add_charge - current_credit - re_val
            
            period_result = {
                "Date": d2.strftime("%d/%m/%Y"),
                "opening_balance": int(round(opening_balance)),
                "opening balance": int(round(opening_balance)),
                "Interest": int(total_int),
                "Service Charge": int(total_sc),
                "Overdue": int(total_od),
                "Additional Charge": float(current_add_charge),
                "Credit Amount": float(current_credit),
                "Rebate": int(re_val),
                "closing_balance": int(round(closing_balance)),
                "closing balance": int(round(closing_balance))
            }
            results.append(period_result)

            accumulated_int += total_int
            accumulated_sc_total += total_sc
            accumulated_od_total += total_od
            accumulated_add_charges += current_add_charge
            accumulated_credits += current_credit
            cumulative_days_before = cumulative_days_after

    elif scheme in GRP4_PARAMS:
        params = GRP4_PARAMS[scheme]
        re_rate_1 = params["rebate_1"]
        re_rate_2 = params["rebate_2"]
        re_rate_3 = params["rebate_3"]
        base_od_rate = params["od_rate"]
        od_inc_days = params["od_inc_days"]

        accumulated_int = 0
        accumulated_sc_total = 0
        accumulated_od_total = 0
        accumulated_rebate = 0
        accumulated_add_charges = 0
        accumulated_credits = 0
        cumulative_days_before = 0

        for i in range(len(dates) - 1):
            opening_balance = pledge_value + accumulated_int + accumulated_sc_total + accumulated_od_total + accumulated_add_charges - accumulated_rebate - accumulated_credits
            d1 = dates[i]
            d2 = dates[i+1]
            diff = (d2 - d1).days

            if i == 0:
                diff += 1

            cumulative_days_after = cumulative_days_before + diff
            total_dues = accumulated_int + accumulated_sc_total + accumulated_od_total + accumulated_add_charges - accumulated_rebate
            excess_credit = max(0, accumulated_credits - total_dues)
            unpaid_add_charges = max(0, accumulated_add_charges - accumulated_credits)
            current_principal = max(0.0, pledge_value + unpaid_add_charges - excess_credit)

            total_sc_unrounded = (current_principal * sc_rate * diff) / 360.0
            total_int_unrounded = 0.0
            total_od_unrounded = 0.0
            total_rebate_unrounded = 0.0

            if diff > 90:
                remaining_days = 90
                running_principal = current_principal
                split_index = 0
               
                while remaining_days > 0:
                    days_to_process = min(remaining_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                    
                    if split_index == 0:
                        applicable_rebate_rate = re_rate_1
                    elif split_index == 1:
                        applicable_rebate_rate = re_rate_2
                    else:
                        applicable_rebate_rate = re_rate_3

                    split_rebate = (running_principal * applicable_rebate_rate * days_to_process) / 360.0
                    total_rebate_unrounded += split_rebate

                    total_int_unrounded += split_int
                    running_principal += split_int
                    remaining_days -= days_to_process
                    split_index += 1
               
                extra_days = diff - 90
               
                while extra_days > 0:
                    days_to_process = min(extra_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                   
                    current_chunk_od_rate = base_od_rate
                    if cumulative_days_after > od_inc_days:
                        current_chunk_od_rate += 0.02

                    split_od = (running_principal * current_chunk_od_rate * days_to_process) / 360.0
                   
                    total_int_unrounded += split_int
                    total_od_unrounded += split_od
                   
                    running_principal += (split_int + split_od)
                    extra_days -= days_to_process

            else:
                remaining_days = diff
                running_principal = current_principal
                
                # FIX: Decide standard rate based on total days instead of progressive slabs
                if diff <= 30:
                    applicable_rebate_rate = re_rate_1
                elif diff <= 60:
                    applicable_rebate_rate = re_rate_2
                else:
                    applicable_rebate_rate = re_rate_3

                while remaining_days > 0:
                    days_to_process = min(remaining_days, 30)
                    split_int = (running_principal * int_rate * days_to_process) / 360.0
                   
                    split_rebate = (running_principal * applicable_rebate_rate * days_to_process) / 360.0

                    total_int_unrounded += split_int
                    total_rebate_unrounded += split_rebate

                    running_principal += split_int
                    remaining_days -= days_to_process

            total_int = round(total_int_unrounded)
            total_sc = round(total_sc_unrounded)
            total_od = round(total_od_unrounded)
            re_val = round(total_rebate_unrounded)
           
            if (d2 - d1).days == 90:
                current_v_od_rate = base_od_rate
                if cumulative_days_after > od_inc_days:
                    current_v_od_rate += 0.02
                V = round((current_principal * re_rate_1 * 30) / 360.0) + round((current_principal * re_rate_2 * 30) / 360.0) + round((current_principal * re_rate_3 * 30) / 360.0) + round((current_principal * current_v_od_rate * 1) / 360.0)
                re_val += V
                total_od = 0
                
            if total_od > 0:
                re_val = 0

            accumulated_rebate += re_val

            current_add_charge = add_charges[i]
            current_credit = credits[i]
            if 30 < (d2-d1).days <= 35:
                total_od = 0
                
            closing_balance = opening_balance + total_int + total_sc + total_od + current_add_charge - current_credit - re_val
            
            period_result = {
                "Date": d2.strftime("%d/%m/%Y"),
                "opening_balance": int(round(opening_balance)),
                "opening balance": int(round(opening_balance)),
                "Interest": int(total_int),
                "Service Charge": int(total_sc),
                "Overdue": int(total_od),
                "Additional Charge": float(current_add_charge),
                "Credit Amount": float(current_credit),
                "Rebate": int(re_val),
                "closing_balance": int(round(closing_balance)),
                "closing balance": int(round(closing_balance))
            }
            results.append(period_result)

            accumulated_int += total_int
            accumulated_sc_total += total_sc
            accumulated_od_total += total_od
            accumulated_add_charges += current_add_charge
            accumulated_credits += current_credit
            cumulative_days_before = cumulative_days_after

    return results 

@app.post("/calculate")
def calculate_rebate(payload: CalculateRequest):
    dates_list = [payload.pledge_date.strip()] + [row.Date.strip() for row in payload.input_df]
    dates_str = ",".join(dates_list)

    add_charges_str = ",".join([str(row.ad_Charges) for row in payload.input_df])
    credits_str = ",".join([str(row.Credit) for row in payload.input_df])

    response = calculate_pledge_values(
        scheme=payload.scheme,
        pledge_value=payload.pledge_value,
        dates_input=dates_str,
        add_charges_input=add_charges_str,
        credits_input=credits_str
    )

    if isinstance(response, dict) and "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])

    return {
        "message": f"Calculation successful for {payload.scheme}.",
        "data": response,
    }