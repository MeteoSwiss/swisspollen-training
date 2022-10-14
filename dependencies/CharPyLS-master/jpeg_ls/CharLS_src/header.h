// 
// (C) Jan de Vaan 2007-2010, all rights reserved. See the accompanying "License.txt" for licensed use. 
// 


#ifndef CHARLS_HEADER
#define CHARLS_HEADER

#include "jpegmarker.h"

#define JPEG_SOI    0xD8 // Start Of Image
#define JPEG_EOI    0xD9 // End Of Image
#define JPEG_SOS    0xDA // Start Of Scan

#define JPEG_SOF_55 0xF7 // Start Of Frame (JPEG-LS encoded)
#define JPEG_LSE    0xF8
#define JPEG_DNL    0xDC
#define JPEG_DRI    0xDD
#define JPEG_RSTm   0xD0
#define JPEG_COM    0xFE
#define JPEG_APP0   0xE0 // Application data 0: used for JFIF header.
#define JPEG_APP7   0xE7 // Application data 7: colorspace
#define JPEG_APP8   0xE8 // Application data 8: colorXForm



// Default bin sizes for JPEG-LS statistical modeling. Can be overriden at compression time, however this is rarely done.
const int BASIC_T1 = 3;
const int BASIC_T2 = 7;
const int BASIC_T3 = 21;

const LONG BASIC_RESET = 64;

class JpegMarkerWriter;


template<class STRATEGY>
class JlsCodecFactory 
{
public:
	std::auto_ptr<STRATEGY> GetCodec(const JlsParameters& info, const JlsCustomParameters&);
private:
	STRATEGY* GetCodecImpl(const JlsParameters& info);
};

JLS_ERROR CheckParameterCoherent(const JlsParameters* pparams);

JlsCustomParameters ComputeDefault(LONG MAXVAL, LONG NEAR);

//
// JpegSegment
//
class JpegSegment
{
protected:
	JpegSegment() {}
public:
	virtual ~JpegSegment() {}
	virtual void Write(JpegMarkerWriter* pstream) = 0;
};

#endif
