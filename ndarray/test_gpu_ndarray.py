import copy

import numpy

import pygpu_ndarray as gpu_ndarray

dtypes_all = ["float32", "float64",
              "int8", "int16", "int32", "int64",
              "uint8", "uint16", "uint32", "uint64",
              "complex64", "complex128",
              ]

dtypes_no_complex = ["float32", "float64",
                     "int8", "int16", "int32", "int64",
                     "uint8", "uint16", "uint32", "uint64",
                     ]

def check_flags(x, y):
    assert x.flags["C_CONTIGUOUS"] == y.flags["C_CONTIGUOUS"]
    assert x.flags["F_CONTIGUOUS"] == y.flags["F_CONTIGUOUS"]
    assert x.flags["WRITEABLE"] == y.flags["WRITEABLE"]
    assert x.flags["OWNDATA"] == y.flags["OWNDATA"]
    assert x.flags["ALIGNED"] == y.flags["ALIGNED"]
    assert x.flags["UPDATEIFCOPY"] == y.flags["UPDATEIFCOPY"]

def check_meta(x, y):
    assert x.shape == y.shape
    assert x.dtype == y.dtype
    assert x.strides == y.strides
    check_flags(x, y)

def check_all(x, y):
    check_meta(x, y)
    assert numpy.allclose(numpy.asarray(x), numpy.asarray(y))

def test_transfer():
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            a = numpy.random.rand(*shp) * 10
            b = gpu_ndarray.GpuNdArrayObject(a)
            c = numpy.asarray(b)

            assert numpy.allclose(c,a)
            assert a.shape == b.shape == c.shape
            assert a.strides == b.strides == c.strides
            assert a.dtype == b.dtype == c.dtype
            assert c.flags.c_contiguous

def test_transfer_not_contiguous():
    """
    Test transfer when the input on the CPU is not contiguous
    TODO: test when the input on the gpu is not contiguous
    """
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            a = numpy.random.rand(*shp) * 10
            a = a[::-1]
            b = gpu_ndarray.GpuNdArrayObject(a)
            c = numpy.asarray(b)

            assert numpy.allclose(c,a)
            assert a.shape == b.shape == c.shape
            # We copy a to a c contiguous array before the transfer
            assert (-a.strides[0],)+a.strides[1:] == b.strides == c.strides
            assert a.dtype == b.dtype == c.dtype
            assert c.flags.c_contiguous

def test_transfer_fortran():
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            a = numpy.random.rand(*shp) * 10
            a_ = numpy.asfortranarray(a)
            if len(shp)>1:
                assert a_.strides != a.strides
            a = a_
            b = gpu_ndarray.GpuNdArrayObject(a)
            c = numpy.asarray(b)

            assert a.shape == b.shape == c.shape
            assert a.dtype == b.dtype == c.dtype
            assert a.flags.f_contiguous
            assert c.flags.f_contiguous
            assert a.strides == b.strides == c.strides
            assert numpy.allclose(c,a)

def test_zeros():
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for order in ["C", "F"]:
            for dtype in dtypes_all:
                x = numpy.zeros(shp, dtype, order)
                y = gpu_ndarray.zeros(shp, dtype, order)
                check_all(x, y)

def test_mapping_getitem_ellipsis():
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            a = numpy.asarray(numpy.random.rand(*shp), dtype=dtype)
            a_gpu = gpu_ndarray.GpuNdArrayObject(a)

            b = a_gpu[...]
            assert b.bytes == a_gpu.bytes
            assert b.strides == a.strides
            assert b.shape == a.shape
            b_cpu = numpy.asarray(b)
            assert numpy.allclose(a, b_cpu)

def test_copy_view():
    from ..array import may_share_memory
    def check_memory_region(a, a_op, b, b_op):
        assert numpy.may_share_memory(a, a_op) == may_share_memory(b, b_op)

        if a_op.base is None:
            assert b_op.base is None
        else:
            assert a_op.base is a and b_op.base is b

    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            #TODO test copy unbroadcast!
            shape = (5,)
            a = numpy.asarray(numpy.random.rand(*shape), dtype='float32')

            b = gpu_ndarray.GpuNdArrayObject(a)
            assert numpy.allclose(a, numpy.asarray(b))
            check_flags(a, b)

            c = b.copy()
            assert numpy.allclose(a, numpy.asarray(c))
            check_flags(c, a.copy())
            check_memory_region(a, a.copy(), b, c)

            d = copy.copy(b)
            assert numpy.allclose(a, numpy.asarray(d))
            check_flags(d, copy.copy(a))
            check_memory_region(a, copy.copy(a), b, d)

            e = b.view()
            assert numpy.allclose(a, numpy.asarray(e))
            check_flags(e, a.view())
            check_memory_region(a, a.view(), b, e)

            f = copy.deepcopy(b)
            assert numpy.allclose(a, numpy.asarray(f))
            check_flags(f, copy.deepcopy(a))
            check_memory_region(a, copy.deepcopy(a), b, f)

            g = copy.copy(b.view())
            assert numpy.allclose(a, numpy.asarray(g))
            check_memory_region(a, copy.copy(a.view()), b, g)
            check_flags(g, copy.copy(a.view()))


def test_len():
    for shp in [(5,),(6,7),(4,8,9),(1,8,9)]:
        for dtype in dtypes_all:
            a = numpy.asarray(numpy.random.rand(*shp), dtype=dtype)
            a_gpu = gpu_ndarray.GpuNdArrayObject(a)
            assert len(a_gpu) == shp[0]

def test_mapping_getitem_w_int():
    def _cmp(x,y):
        assert x.shape == y.shape
        assert x.dtype == y.dtype
        assert x.strides == y.strides
        assert x.flags["C_CONTIGUOUS"] == y.flags["C_CONTIGUOUS"]
        assert x.flags["F_CONTIGUOUS"] == y.flags["F_CONTIGUOUS"]
        if x.flags["WRITEABLE"] != y.flags["WRITEABLE"]:
            assert x.ndim == 0
            assert not x.flags["OWNDATA"]
            assert y.flags["OWNDATA"]
        else:
            assert x.flags["WRITEABLE"] == y.flags["WRITEABLE"]
            assert x.flags["OWNDATA"] == y.flags["OWNDATA"]
        assert x.flags["ALIGNED"] == y.flags["ALIGNED"]
        assert x.flags["UPDATEIFCOPY"] == y.flags["UPDATEIFCOPY"]
        x = numpy.asarray(x)
        assert x.shape == y.shape
        assert x.dtype == y.dtype
        assert x.strides == y.strides
        if not numpy.all(x == y):
            print x
            print y
        assert numpy.all(x == y),(x, y)

    def _cmpNs(x,y):
        """
        Don't compare the stride after the transfer
        There is a copy that have been made on the gpu before the transfer
        """
        assert x.shape == y.shape
        assert x.dtype == y.dtype
        assert x.strides == y.strides
        assert x.flags["C_CONTIGUOUS"] == y.flags["C_CONTIGUOUS"]
        assert x.flags["F_CONTIGUOUS"] == y.flags["F_CONTIGUOUS"]
        assert x.flags["WRITEABLE"] == y.flags["WRITEABLE"]
        assert x.flags["ALIGNED"] == y.flags["ALIGNED"]
        assert x.flags["OWNDATA"] == y.flags["OWNDATA"]
        assert x.flags["UPDATEIFCOPY"] == y.flags["UPDATEIFCOPY"]
        x_ = numpy.asarray(x)
        assert x_.shape == y.shape
        assert x_.dtype == y.dtype
        if not numpy.all(x_ == y):
            print x_
            print y
        assert numpy.all(x_ == y),(x_, y)
        pass
    def _cmpf(x,*y):
        try:
            x.__getitem__(y)
        except IndexError:
            pass
        else:
            raise Exception("Did not generate out or bound error")

    def _cmpfV(x,*y):
        try:
            if len(y)==1:
                x.__getitem__(*y)
            else:
                x.__getitem__(y)
        except ValueError:
            pass
        else:
            raise Exception("Did not generate value error")

    for dtype in dtypes_all:

        # test vector
        dim =(2,)
        a = numpy.asarray(numpy.random.rand(*dim)*10, dtype=dtype)
        _a = gpu_ndarray.GpuNdArrayObject(a)
        import sys
        init_ref_count = sys.getrefcount(_a)
        _cmp(_a[...], a[...])
        _cmp(_a[...], a[...])
        _cmp(_a[...], a[...])
        _cmp(_a[...], a[...])
        _cmp(_a[...], a[...])


        _cmp(_a[-1], a[-1])
        _cmp(_a[1], a[1])
        _cmp(_a[0], a[0])
        _cmp(_a[::1], a[::1])
        _cmpNs(_a[::-1], a[::-1])
        _cmp(_a[...], a[...])
        _cmpf(_a,2)

        # test scalar
        dim =()
        a = numpy.asarray(numpy.random.rand(*dim)*10, dtype=dtype)
        _a = gpu_ndarray.GpuNdArrayObject(a)
        _cmp(_a[...], a[...])
        _cmpf(_a,0)
        _cmpfV(_a,slice(1))

        # test 4d-tensor
        dim =(5,4,3,2)
        a = numpy.asarray(numpy.random.rand(*dim)*10, dtype=dtype)
        _a = gpu_ndarray.GpuNdArrayObject(a)
        _cmpf(_a,slice(-1),slice(-1),10,-10)
        _cmpf(_a,slice(-1),slice(-1),-10,slice(-1))
        _cmpf(_a,0,slice(0,-1,-20),-10)
        _cmpf(_a,10)
        _cmpf(_a,(10,0,0,0))
        _cmpf(_a,-10)

        #test with integer
        _cmp(_a[1], a[1])
        _cmp(_a[-1], a[-1])
        _cmp(_a[numpy.int64(1)], a[numpy.int64(1)])
        _cmp(_a[numpy.int64(-1)], a[numpy.int64(-1)])

        #test with slice
        _cmp(_a[1:], a[1:])
        _cmp(_a[1:2], a[1:2])
        _cmp(_a[-1:1], a[-1:1])

        #test with tuple (mix slice, integer, numpy.int64)
        _cmpNs(_a[0,0,::numpy.int64(-1), ::-1], a[0,0,::-1,::-1])
        _cmpNs(_a[:,:,::numpy.int64(-1), ::-1], a[:,:,::-1,::-1])
        _cmpNs(_a[:,:,numpy.int64(1),-1], a[:,:,1,-1])
        _cmpNs(_a[:,:,::-1, ::-1], a[:,:,::-1,::-1])
        _cmpNs(_a[:,:,::-10, ::-10], a[:,:,::-10,::-10])
        _cmpNs(_a[:,:,1,-1], a[:,:,1,-1])
        _cmpNs(_a[:,:,-1,:], a[:,:,-1,:])
        _cmpNs(_a[:,::-2,-1,:], a[:,::-2,-1,:])
        _cmpNs(_a[:,::-20,-1,:], a[:,::-20,-1,:])
        _cmpNs(_a[:,::-2,-1], a[:,::-2,-1])
        _cmpNs(_a[0,::-2,-1], a[0,::-2,-1])
        _cmp(_a[-1,-1,-1,-2], a[-1,-1,-1,-2])

        #test ellipse
        _cmp(_a[...], a[...])
