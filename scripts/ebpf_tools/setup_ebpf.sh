#!/bin/bash

apt-get install -y \
	tmux \
	curl \
	wget \
	software-properties-common \
	pkg-config \
	binutils-dev \
	libcap-dev \
	libelf-dev \
	gcc-multilib \
	gpg \
	vim \
	universal-ctags \
	cmake \
	libssl-dev \
	libcurl4-openssl-dev \
	tcpdump \
	net-tools \
	fakeroot \
	build-essential \
	ncurses-dev \
	xz-utils

install latest llvm for ebpf
mkdir -p /opt/llvm && cd /opt/llvm && \
	wget https://apt.llvm.org/llvm.sh && \
	chmod +x llvm.sh && \
	./llvm.sh all && \
	wget https://raw.githubusercontent.com/ShangjinTang/dotfiles/05ef87daae29475244c276db5d406b58c52be445/linux/ubuntu/22.04/bin/update-alternatives-clang && \
	chmod +x update-alternatives-clang && \
	sed -i 's/sudo//g' update-alternatives-clang && \
	./update-alternatives-clang

# update cache for dynamic libraries
ldconfig

git clone https://github.com/netgroup/libbpf-bootstrap-tc.git

cd libbpf-bootstrap-tc

git checkout andrea-tests

git submodule update --init --recursive

cd examples/c

make -j8


