<!-- v.20191210.0 -->
<!DOCTYPE html>
<HTML>
<HEAD>
<META http-equiv="Content-Type" content="text/html; charset=utf-8" />
<TITLE></TITLE>
</HEAD>
<BODY>

<?php
	if(isset($_GET['oauth_token'])) { $oatoken = $_GET['oauth_token'];}
	if(isset($_GET['oauth_verifier'])) { $oaveri = $_GET['oauth_verifier'];}
	if (isset($oatoken) && isset($oaveri)) {
		$command="python3 /var/www/cgi-bin/tokenview.py ".$oatoken." ".$oaveri; ?>
		exec($command,$output);
		echo $output[0];
	} else {
		$command="python3 /var/www/cgi-bin/tokenview.py";
		exec($command,$output);
		if(isset($output)) { print "<a href=$output[0]>link</a>"; }
	}

?>

<hr>
<a href="../../index.php">back</a>

</BODY>
</HTML>
