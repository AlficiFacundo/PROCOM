#include <stdio.h>
#include <string.h>
#include "xparameters.h"
#include "xil_cache.h"
#include "xgpio.h"
#include "platform.h"
#include "xuartlite.h"

#define PORT_IN	 		XPAR_AXI_GPIO_0_BASEADDR
#define PORT_OUT 		XPAR_AXI_GPIO_0_BASEADDR

// Dispositivos
#define DEV_LED0        0x00
#define DEV_LED1        0x01
#define DEV_LED2        0x02
#define DEV_LED3        0x03
#define DEV_READ_SW     0x04

// Bits de color dentro del byte de Data (DEV_LEDx)
#define COLOR_R   0x01
#define COLOR_G   0x02
#define COLOR_B   0x04

#define DATA_BUF_MAX 64

XGpio GpioOutput;
XGpio GpioInput;
u32 GPO_Value = 0x00000000;
XUartLite uart_module;

typedef struct {
    u8  is_long;
    u8  device;
    u16 size;
} Header;

static void read_bytes(u8 *buf, int n){
    int i=0;
    //Polling de recepción de cada Byte enviado a traves del uart.(XUartLite_Recv es no bloqueante, es decir que no espera
    // a que se reciba el byte, simplemente se fija lo que hay y lo toma.) 
    while(i<n){
        unsigned int recv = XUartLite_Recv(&uart_module, &buf[i], (unsigned int) 1);
        if(recv>0){
            i++;
        }
    }
}

static void send_bytes(u8 *buf, int n){
    //Mira la flag para saber si ya está enviando algo ---> True : Bucle vacío.
    while(XUartLite_IsSending(&uart_module)){}
    XUartLite_Send(&uart_module, buf, n);
}

static int read_header(Header *h){
    // Lee los 4 bytes de cabecera. Devuelve -1 si no matchea el patron 101.
    u8 b[4];
    read_bytes(b,4); //Extraer el 101 de transmisión

    if(((b[0]>>5)&0x07) != 0x05){   
        return -1; //Si no es 101, return -1 para indicar solapamiento de transmisiones.
    }

    h->is_long = (b[0]>>4)&0x01;
    h->device  = b[3];

    if(h->is_long){
        h->size = ((u16)b[1]<<8) | b[2]; //total de large
    } else {
        h->size = b[0]&0x0F; //total de short
    }
    return 0;
}


static int read_trailer(Header *h){
    // Lee el byte de fin de trama (010 + L/S + S.Size) y lo valida contra
    // los mismos campos leidos en la cabecera. Devuelve -1 si hay diferencias.
    u8 t;
    read_bytes(&t,1);

    if(((t>>5)&0x07) != 0x02){
        return -1; //Si no es 010, return -1 para indicar error de transmisión.
    }

    u8 t_is_long = (t>>4)&0x01;
    if(t_is_long != h->is_long){
        return -1; // Si hay una diferencia del L/S, se devuelve error de transmisión
    }

    if(!h->is_long){
        u8 t_size = t & 0x0F;
        if(t_size != (h->size & 0x0F)){
            return -1; // De igual manera, si difieren los L/S, error de transmisión.
        }
    }
    return 0;
}

static void build_and_send_frame(u8 device, u8 *data, u16 size){
    // Arma y envia una trama completa (cabecera + data + fin de trama)
    u8 hdr[4]; //header
    u8 trl[1]; //trailer o cola
    u8 is_long = (size>15); // longitud de trama

    if(is_long){
        //construcción para trama larga 
        hdr[0] = (0x05<<5) | (0x01<<4); //10110
        hdr[1] = (u8)(size>>8); //sizeH
        hdr[2] = (u8)(size&0xFF); //sizeL
        trl[0] = (0x02<<5) | (0x01<<4); //01010
    } else {
        //construcción para trama corta 
        hdr[0] = (0x05<<5) | (size&0x0F); //1010+size
        hdr[1] = 0x00; //sizeL = 0
        hdr[2] = 0x00; //sizeH = 0
        trl[0] = (0x02<<5) | (size&0x0F); //0100+size
    }
    hdr[3] = device;

    //enviar header, luego data y por ultimo trailer.
    send_bytes(hdr,4); 
    if(size>0){
        send_bytes(data,size); 
    }
    send_bytes(trl,1);
}

int main()
{
    init_platform();
    int Status;
    XUartLite_Initialize(&uart_module, 0);

    Status = XGpio_Initialize(&GpioInput, PORT_IN);
    if(Status!=XST_SUCCESS){ return XST_FAILURE; }
    Status = XGpio_Initialize(&GpioOutput, PORT_OUT);
    if(Status!=XST_SUCCESS){ return XST_FAILURE; }

    XGpio_SetDataDirection(&GpioOutput,1,0x00000000);
    XGpio_SetDataDirection(&GpioInput,1,0xFFFFFFFF);

    while(1){
        Header h;
        if(read_header(&h)!=0){
            continue; //esperar trama, vuelve.
        }

        u8 data[DATA_BUF_MAX];
        if(h.size>0 && h.size<=DATA_BUF_MAX){
            read_bytes(data,h.size); //limita la capacidad de data.
        }

        if(read_trailer(&h)!=0){
            continue; // si el trailer no matchea con la cabecera, se descarta la trama
        }

        switch(h.device){
            case DEV_LED0:
            case DEV_LED1:
            case DEV_LED2:
            case DEV_LED3: {
                int led = h.device;
                u8 color = (h.size>0)? data[0] : 0x00; //guardar color
                u32 mask  = 0x07u << (led*3); //calcular mascara segun el led
                u32 value = (u32)(color & 0x07) << (led*3); //calcular valor del color seleccionado
                GPO_Value = (GPO_Value & ~mask) | value;
                XGpio_DiscreteWrite(&GpioOutput,1,GPO_Value);
                break;
            }
            case DEV_READ_SW: {
                u32 sw = XGpio_DiscreteRead(&GpioInput,1); //leer gpio entero
                u8 resp = (u8)(sw & 0x0F); //mascara con los bits del sw
                build_and_send_frame(DEV_READ_SW,&resp,1); //enviar trama a python
                break;
            }
            default:
                break;
        }
    }
    cleanup_platform();
    return 0;
}