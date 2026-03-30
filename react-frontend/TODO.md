# TODO

* need to update to work with the lambda changes once theyre done

* wg config needs to pull way more from secrets, not just the keys

* only 1 region needs to be available now, still keep the drop down tho probably just have the first entry preselected which will be CA

* terraform and cleanup is no longer needed

* keep the table

* update about page to not bold the conf and maybe change wording to OCI but prolly now

* table should always be there but just have no data when the user has no vpns and show loading instead of hiding the table. show a placeholder or something.

* Handle new statuses for vpns in firebase:
  - `Pending`
  - `Running`
  - `Failed`
  - `Terminated`