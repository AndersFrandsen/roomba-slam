# openblas lives in meta-python-ai, which pulls in a clang layer;
# use the reference BLAS from lapack (meta-oe) instead
DEPENDS:remove = "openblas"
DEPENDS += "lapack"
EXTRA_OECMAKE:remove = "-DSUITESPARSE_USE_64BIT_BLAS=ON"
EXTRA_OECMAKE += "-DSUITESPARSE_USE_64BIT_BLAS=OFF -DBLA_VENDOR=Generic"
