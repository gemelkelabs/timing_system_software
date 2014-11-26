<?php
if ($_REQUEST['folder']=='none') {
	$folders=scandir("../../psu_data/sequences");
	$folders=array_reverse($folders);
		// Reorder folders by date
		for ($j=0;$j<count($folders);$j++){
			IF ($folders[$j]=='.'){continue;}
			IF ($folders[$j]=='..'){continue;}
			$dateparts=explode('-',$folders[$j]);
			IF (count($dateparts)==3){
				$folderdates[$j]=strtotime($dateparts[2].'/'.$dateparts[0].'/'.$dateparts[1]);
				$folderskeyedbydate[$folderdates[$j]]=$folders[$j];
			}
		}
	ksort($folderskeyedbydate);
	$folders=array_reverse($folderskeyedbydate);
		
	for ($j=0;$j<count($folders);$j++){
		IF ($folders[$j]=='.'){continue;}
		IF ($folders[$j]=='..'){continue;}
		IF (strpos($folders[$j],'.xml') === false) {
			print($folders[$j]);
		} ELSE {
			print('EXCLUDE_ME');
		}
		if ($j != (count($folders)-1)) {print(",");}
		}
} else {
	$files=scandir("../../psu_data/sequences".$_REQUEST['folder']);
	for ($j=0;$j<count($files);$j++){
		IF ($files[$j]=='.'){continue;}
		IF ($files[$j]=='..'){continue;}
		print($files[$j]);
		if ($j != (count($files)-1)) {print(",");}		
		}
}
?>