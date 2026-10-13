set pagination off
set breakpoint pending on
break GTKNoCSDGetReferences
commands 1
silent
printf "GetReferences(%d) before: version=%d gottypes=%d window=%lu\n", $rdi, *(int*)&GTKNoCSDGTKVersion, *(char*)&GTKNoCSDGotTypes, *(unsigned long*)&GTKNoCSDGTKWindow
continue
end
break _exit
commands 2
silent
printf "AT EXIT: version=%d gottypes=%d GTKNoCSDGTKWindow=%lu\n", *(int*)&GTKNoCSDGTKVersion, *(char*)&GTKNoCSDGotTypes, *(unsigned long*)&GTKNoCSDGTKWindow
continue
end
run
