$root = $PSScriptRoot
$regionsSource = Get-Content (Join-Path $root 'regions.js') -Raw -Encoding UTF8
$regionsBlock = ($regionsSource -split 'window\.ipsiSubregions\s*=')[0]
$regionsJson = $regionsBlock.Replace('window.ipsiRegions =', '').Trim().TrimEnd(';').Replace("'", '"')
$regions = $regionsJson | ConvertFrom-Json

$baseUrl = 'https://ipsiguide.kr'
$servicePages = @(
  'form.html',
  'cities.html',
  'tutoring.html',
  'essay-tutoring.html',
  'jungsi-tutoring.html'
)
$districtPages = @(
  'district.html',
  'tutoring-district.html',
  'essay-tutoring-district.html',
  'jungsi-tutoring-district.html'
)

$urls = [System.Collections.Generic.List[string]]::new()
$urls.Add("$baseUrl/")
foreach ($page in $servicePages) {
  $urls.Add("$baseUrl/$page")
}

foreach ($regionProperty in $regions.PSObject.Properties) {
  $region = [uri]::EscapeDataString($regionProperty.Name)
  foreach ($districtName in $regionProperty.Value) {
    $district = [uri]::EscapeDataString($districtName)
    foreach ($page in $districtPages) {
      $urls.Add("$baseUrl/$page`?region=$region&district=$district")
    }
  }
}

$entries = foreach ($url in $urls) {
  $escapedUrl = [Security.SecurityElement]::Escape($url)
  "  <url>`n    <loc>$escapedUrl</loc>`n  </url>"
}
$sitemap = "<?xml version=`"1.0`" encoding=`"UTF-8`"?>`n<urlset xmlns=`"http://www.sitemaps.org/schemas/sitemap/0.9`">`n$($entries -join "`n")`n</urlset>`n"
$utf8WithoutBom = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $root 'sitemap.xml'), $sitemap, $utf8WithoutBom)

Write-Output "Generated sitemap.xml with $($urls.Count) URLs."