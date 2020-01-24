
$string_ids = @()

Select-String -path resources\language\resource.language.en_gb\strings.po -pattern "msgctxt " | select Line | ForEach {
	$id = [regex]::match($_.Line.ToString(), '\"#([0-9]+)\"').Groups[1].Value
	if($string_ids -contains $id)
	{
	   Write-Host "ERROR: String ID Already Exists : " $id
	}
	else
	{
	   $string_ids += $id
	   Get-ChildItem *.py,settings.xml,resources\language\resource.language.en_gb\strings.po -recurse | Select-String -pattern $id | group Pattern | where {$_.Count -eq 1} | select Name, Count
	}
}
