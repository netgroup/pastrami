#!/bin/bash

pushd /opt

apt update
sleep 5

apt install -y linux-image-unsigned-5.19.0-50-generic linux-headers-5.19.0-50-generic linux-modules-5.19.0-50-generic linux-modules-extra-5.19.0-50-generic
sleep 5

apt install -y linux-image-unsigned-6.2.0-39-generic linux-headers-6.2.0-39-generic linux-modules-6.2.0-39-generic linux-modules-extra-6.2.0-39-generic
sleep 5

apt install -y linux-image-unsigned-6.5.0-45-generic linux-headers-6.5.0-45-generic linux-modules-6.5.0-45-generic linux-modules-extra-6.5.0-45-generic
sleep 5

apt install -y linux-image-unsigned-6.8.0-52-generic linux-headers-6.8.0-52-generic linux-modules-6.8.0-52-generic linux-modules-extra-6.8.0-52-generic
sleep 5


#APT_VER=("5.19.0-50" "6.2.0-39" "6.5.0-45" "6.8.0-52")
#for VER in "${APT_VER[@]}"; do
#    echo "apt install -y linux-image-unsigned-${VER}-generic linux-headers-${VER}-generic linux-modules-${VER}-generic linux-modules-extra-${VER}-generic"
#    apt install -y linux-image-unsigned-${VER}-generic linux-headers-${VER}-generic linux-modules-${VER}-generic linux-modules-extra-${VER}-generic
#done


# https://kernel.ubuntu.com/mainline/
#PPA_VER=("6.10.14" "6.12.17" "6.13.5" "6.14-rc5")

## 5.6.19
#mkdir  -p v5.6.19
#cd v5.6.19
#wget https://kernel.ubuntu.com/mainline/v5.6.19/amd64/linux-headers-5.6.19-050619-generic_5.6.19-050619.202006171132_amd64.deb
#wget https://kernel.ubuntu.com/mainline/v5.6.19/amd64/linux-headers-5.6.19-050619_5.6.19-050619.202006171132_all.deb
#wget https://kernel.ubuntu.com/mainline/v5.6.19/amd64/linux-image-unsigned-5.6.19-050619-generic_5.6.19-050619.202006171132_amd64.deb
#wget https://kernel.ubuntu.com/mainline/v5.6.19/amd64/linux-modules-5.6.19-050619-generic_5.6.19-050619.202006171132_amd64.deb
#dpkg -i *.deb
#cd ..


## 5.8.18
#mkdir  -p v5.8.18
#cd v5.8.18
#wget https://kernel.ubuntu.com/mainline/v5.8.18/amd64/linux-headers-5.8.18-050818-generic_5.8.18-050818.202011011237_amd64.deb
#wget https://kernel.ubuntu.com/mainline/v5.8.18/amd64/linux-headers-5.8.18-050818_5.8.18-050818.202011011237_all.deb
#wget https://kernel.ubuntu.com/mainline/v5.8.18/amd64/linux-image-unsigned-5.8.18-050818-generic_5.8.18-050818.202011011237_amd64.deb
#wget https://kernel.ubuntu.com/mainline/v5.8.18/amd64/linux-modules-5.8.18-050818-generic_5.8.18-050818.202011011237_amd64.deb
#dpkg -i *.deb
#cd ..


# 5.10.234
mkdir  -p v5.10.234
cd v5.10.234
wget https://kernel.ubuntu.com/mainline/v5.10.234/amd64/linux-headers-5.10.234-0510234-generic_5.10.234-0510234.202502020502_amd64.deb
wget https://kernel.ubuntu.com/mainline/v5.10.234/amd64/linux-headers-5.10.234-0510234_5.10.234-0510234.202502020502_all.deb
wget https://kernel.ubuntu.com/mainline/v5.10.234/amd64/linux-image-unsigned-5.10.234-0510234-generic_5.10.234-0510234.202502020502_amd64.deb
wget https://kernel.ubuntu.com/mainline/v5.10.234/amd64/linux-modules-5.10.234-0510234-generic_5.10.234-0510234.202502020502_amd64.deb
dpkg -i *.deb
cd ..


# 5.12.19
mkdir  -p v5.12.19
cd v5.12.19
wget https://kernel.ubuntu.com/mainline/v5.12.19/amd64/linux-headers-5.12.19-051219-generic_5.12.19-051219.202107201136_amd64.deb
wget https://kernel.ubuntu.com/mainline/v5.12.19/amd64/linux-headers-5.12.19-051219_5.12.19-051219.202107201136_all.deb
wget https://kernel.ubuntu.com/mainline/v5.12.19/amd64/linux-image-unsigned-5.12.19-051219-generic_5.12.19-051219.202107201136_amd64.deb
wget https://kernel.ubuntu.com/mainline/v5.12.19/amd64/linux-modules-5.12.19-051219-generic_5.12.19-051219.202107201136_amd64.deb
dpkg -i *.deb
cd ..


# 6.10.14
mkdir  -p v6.10.14
cd v6.10.14
wget https://kernel.ubuntu.com/mainline/v6.10.14/amd64/linux-headers-6.10.14-061014-generic_6.10.14-061014.202411070043_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.10.14/amd64/linux-headers-6.10.14-061014_6.10.14-061014.202411070043_all.deb
wget https://kernel.ubuntu.com/mainline/v6.10.14/amd64/linux-image-unsigned-6.10.14-061014-generic_6.10.14-061014.202411070043_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.10.14/amd64/linux-modules-6.10.14-061014-generic_6.10.14-061014.202411070043_amd64.deb

dpkg -i *.deb
cd ..


# 6.12.17
mkdir  -p v6.12.17
cd v6.12.17
wget https://kernel.ubuntu.com/mainline/v6.12.17/amd64/linux-headers-6.12.17-061217-generic_6.12.17-061217.202502271349_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.12.17/amd64/linux-headers-6.12.17-061217_6.12.17-061217.202502271349_all.deb
wget https://kernel.ubuntu.com/mainline/v6.12.17/amd64/linux-image-unsigned-6.12.17-061217-generic_6.12.17-061217.202502271349_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.12.17/amd64/linux-modules-6.12.17-061217-generic_6.12.17-061217.202502271349_amd64.deb

dpkg -i *.deb
cd ..


# 6.13.5
mkdir  -p v6.13.5
cd v6.13.5
wget https://kernel.ubuntu.com/mainline/v6.13.5/amd64/linux-headers-6.13.5-061305-generic_6.13.5-061305.202502271338_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.13.5/amd64/linux-headers-6.13.5-061305_6.13.5-061305.202502271338_all.deb
wget https://kernel.ubuntu.com/mainline/v6.13.5/amd64/linux-image-unsigned-6.13.5-061305-generic_6.13.5-061305.202502271338_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.13.5/amd64/linux-modules-6.13.5-061305-generic_6.13.5-061305.202502271338_amd64.deb

dpkg -i *.deb
cd ..

# 6.14-rc5
mkdir  -p v6.14-rc5
cd v6.14-rc5
wget https://kernel.ubuntu.com/mainline/v6.14-rc5/amd64/linux-headers-6.14.0-061400rc5-generic_6.14.0-061400rc5.202503022109_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.14-rc5/amd64/linux-headers-6.14.0-061400rc5_6.14.0-061400rc5.202503022109_all.deb
wget https://kernel.ubuntu.com/mainline/v6.14-rc5/amd64/linux-image-unsigned-6.14.0-061400rc5-generic_6.14.0-061400rc5.202503022109_amd64.deb
wget https://kernel.ubuntu.com/mainline/v6.14-rc5/amd64/linux-modules-6.14.0-061400rc5-generic_6.14.0-061400rc5.202503022109_amd64.deb

dpkg -i *.deb
cd ..

popd
