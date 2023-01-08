# RDBatch
Batch Cart Field Importer for Rivendell Radio Automation

RDBatch uses the Rivendell CWebAPI to post cart and cut updates.

## Before You Begin

RDBatch uses the `Cart Data Dump (CSV)` report generated within RDLibrary. Create this report and make any changes within your favorite CSV editor.

## Usage

There are several constants located at the top of the script `rdbatch.py` which can be edited to suit your needs.

| Constant | Type | Description |
|--|--|--|
| `CSV_FILE` | `str` | Absolute or relative path to the Cart Data Dump CSV file. |
| `RD_HOST` | `str` | IP address or hostname of a host on your rivendell system. |
| `RD_USER` | `str` | Authorized Rivendell user to make edits as. |
| `RD_PSWD` | `str` | The password for the above user. |
| `UPDATE_CARTS` | `bool` | Set flag to update cart fields. |
| `UPDATE_CUTS` | `bool` | Set flag to update cut fields. |
| `UPDATE_SCHED_CODES` | `bool` | Set flag to assign sched codes. |

## Limitations

- Timing markers are not currently supported.

## Scheduler Codes

Scheduler codes are added to the column directly to the right of the `SCHED_CODES` column. Multiple codes can be added, and should be delimited with a `|` character.